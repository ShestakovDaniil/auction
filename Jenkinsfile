pipeline {
    agent any

    options {
        skipDefaultCheckout()
        skipStagesAfterUnstable()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '12', artifactNumToKeepStr: '8'))
        timeout(time: 45, unit: 'MINUTES')
        timestamps()
    }

    environment {
        TOOL_IMAGE = 'auction-ci-tools:lab5'
        REGISTRY = 'registry:5000'
    }

    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
                script {
                    env.COMMIT_SHA = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                    env.RUN_KEY = "auction-ci-${env.BUILD_NUMBER}-" + sh(
                        script: 'cut -c1-12 /proc/sys/kernel/random/uuid',
                        returnStdout: true
                    ).trim()
                    env.CANDIDATE_IMAGE = "auction-ci:${env.COMMIT_SHA}-${env.RUN_KEY}"
                    env.RELEASE_IMAGE = "${env.REGISTRY}/auction:${env.COMMIT_SHA}"
                }
                sh 'mkdir -p reports && docker info --format "{{.Name}} {{.ServerVersion}}"'
            }
        }

        stage('Secrets') {
            steps {
                sh '''
                    docker run --rm --user "$(id -u):$(id -g)" \
                        --mount "type=bind,src=$WORKSPACE,dst=/src,readonly" \
                        --mount "type=bind,src=$WORKSPACE/reports,dst=/reports" \
                        ghcr.io/gitleaks/gitleaks:v8.30.1 git \
                        --config /src/.ci/gitleaks.toml --log-opts=HEAD \
                        --redact=100 --report-format json --report-path /reports/gitleaks.json /src
                '''
            }
        }

        stage('Dependencies and test DB') {
            steps {
                sh '''
                    set +x
                    docker build -f .ci/Checks.Dockerfile -t "$TOOL_IMAGE" .ci
                    docker network create "$RUN_KEY"
                    db_password=$(tr -d '-' < /proc/sys/kernel/random/uuid)
                    export MARIADB_PASSWORD="$db_password"
                    export DB_PASSWORD="$db_password"
                    export APP_SECRET_KEY="$(tr -d '-' < /proc/sys/kernel/random/uuid)$(tr -d '-' < /proc/sys/kernel/random/uuid)"
                    export TEST_DATABASE_URL="mysql+pymysql://auction_ci:$db_password@db:3306/auction_ci_test?charset=utf8mb4"
                    docker run --detach --name "$RUN_KEY-db" --network "$RUN_KEY" --network-alias db \
                        --memory 1536m --cpus 1 \
                        -e MARIADB_DATABASE=auction_ci_test -e MARIADB_USER=auction_ci \
                        -e MARIADB_RANDOM_ROOT_PASSWORD=yes -e MARIADB_PASSWORD mariadb:11.4.12
                    docker run --detach --name "$RUN_KEY-tools" --network "$RUN_KEY" \
                        --user "$(id -u):$(id -g)" --memory 1536m --cpus 2 \
                        -e HOME=/tmp -e TEST_DATABASE_URL -e APP_SECRET_KEY -e DB_PASSWORD \
                        --mount "type=bind,src=$WORKSPACE,dst=/work" \
                        --mount type=volume,src=auction-pip-cache,dst=/pip-cache \
                        "$TOOL_IMAGE" sleep infinity
                    docker exec "$RUN_KEY-tools" sh -ec '
                        python -m venv .venv
                        .venv/bin/python -m pip install pip==26.3
                        .venv/bin/python -m pip install -r requirements-dev.txt
                        .venv/bin/python -m pip check
                    '
                '''
            }
        }

        stage('Style and static analysis') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail
docker exec "$RUN_KEY-tools" make quality \
    'RUFF_FLAGS=--output-format=json --output-file=reports/ruff.json' \
    'BANDIT_FLAGS=-f json -o reports/bandit.json' 2>&1 | tee reports/quality.log
'''
            }
        }

        stage('Tests') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail
ready=0
for attempt in {1..45}; do
    if docker exec "$RUN_KEY-db" healthcheck.sh --connect --innodb_initialized; then
        ready=1
        break
    fi
    sleep 2
done
if [[ $ready -ne 1 ]]; then
    echo 'CI MariaDB failed its readiness check' >&2
    exit 1
fi
docker exec "$RUN_KEY-tools" make test mutation-check compile-check 2>&1 | tee reports/tests.log
test -s reports/junit.xml
'''
            }
            post {
                always {
                    junit testResults: 'reports/junit.xml', allowEmptyResults: true
                }
            }
        }

        stage('Migrations') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail
docker exec "$RUN_KEY-tools" sh -ec '
    DATABASE_URL="$TEST_DATABASE_URL" make migrate migration-state
' 2>&1 | tee reports/migrations.log
'''
            }
        }

        stage('Backup') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail
docker exec "$RUN_KEY-tools" sh -ec '
    DATABASE_URL="$TEST_DATABASE_URL" make backup
    set -- backups/auction_ci_test-*.sql.gz
    test "$#" -eq 1
    test -s "$1"
    gzip -t "$1"
    echo "Backup archive integrity: OK"
' 2>&1 | tee reports/backup.log
'''
            }
        }

        stage('Dependency security') {
            steps {
                sh '''
                    docker exec "$RUN_KEY-tools" sh -ec '
                        pip-audit --path .venv/lib/python3.12/site-packages --strict --progress-spinner off --format json --output reports/pip-audit.json
                    '
                '''
            }
        }

        stage('Build candidate') {
            steps {
                sh '''
                    docker build --pull --label "org.opencontainers.image.revision=$COMMIT_SHA" \
                        --tag "$CANDIDATE_IMAGE" .
                    docker image inspect --format '{{.Id}}' "$CANDIDATE_IMAGE" > reports/image-id.txt
                '''
            }
        }

        stage('Container check') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail
set +x
docker rm -fv "$RUN_KEY-db"
export DB_PASSWORD=$(tr -d '-' < /proc/sys/kernel/random/uuid)
export APP_SECRET_KEY="$(tr -d '-' < /proc/sys/kernel/random/uuid)$(tr -d '-' < /proc/sys/kernel/random/uuid)"
docker run --rm --name "$RUN_KEY-compose" \
    --mount "type=bind,src=$WORKSPACE,dst=/work,readonly" \
    --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
    -e DB_PASSWORD -e APP_SECRET_KEY -e "AUCTION_CHECK_IMAGE=$CANDIDATE_IMAGE" \
    "$TOOL_IMAGE" make container-check 2>&1 | tee reports/container-check.log
'''
            }
        }

        stage('Image security') {
            steps {
                sh '''
                    docker image save --output candidate.tar "$CANDIDATE_IMAGE"
                    scan_image() {
                        docker run --rm \
                            --mount "type=bind,src=$WORKSPACE,dst=/src,readonly" \
                            --mount type=volume,src=auction-trivy-cache,dst=/cache \
                            ghcr.io/aquasecurity/trivy:0.74.0 \
                            --config /src/.ci/trivy.yaml --cache-dir /cache image \
                            --ignorefile /dev/null --input /src/candidate.tar "$@"
                    }
                    scan_image --exit-code 0 > reports/trivy.json
                    scan_image --ignore-unfixed > reports/trivy-gate.json
                '''
            }
        }

        stage('Publish') {
            when {
                allOf {
                    branch 'develop'
                    not { changeRequest() }
                }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'auction-registry-push',
                    usernameVariable: 'REGISTRY_USER',
                    passwordVariable: 'REGISTRY_PASSWORD'
                )]) {
                    sh '''
                        set +x
                        export DOCKER_CONFIG=$(mktemp -d)
                        trap 'rm -rf "$DOCKER_CONFIG"' EXIT
                        printf '%s' "$REGISTRY_PASSWORD" | docker login "$REGISTRY" --username "$REGISTRY_USER" --password-stdin
                        test "$(docker image inspect --format '{{.Id}}' "$CANDIDATE_IMAGE")" = "$(cat reports/image-id.txt)"
                        docker tag "$CANDIDATE_IMAGE" "$RELEASE_IMAGE"
                        docker push "$RELEASE_IMAGE"
                        printf '%s\n' "$RELEASE_IMAGE" > reports/published-image.txt
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
        cleanup {
            sh '''
                set +x
                rm -f candidate.tar
                if [ -n "${RUN_KEY:-}" ]; then
                    for suffix in compose tools db; do
                        if docker container inspect "$RUN_KEY-$suffix" >/dev/null 2>&1; then
                            docker rm -fv "$RUN_KEY-$suffix"
                        fi
                    done
                    if docker network inspect "$RUN_KEY" >/dev/null 2>&1; then
                        docker network rm "$RUN_KEY"
                    fi
                fi
                for image in "${RELEASE_IMAGE:-}" "${CANDIDATE_IMAGE:-}"; do
                    if [ -n "$image" ] && docker image inspect "$image" >/dev/null 2>&1; then
                        docker image rm "$image"
                    fi
                done
            '''
        }
    }
}
