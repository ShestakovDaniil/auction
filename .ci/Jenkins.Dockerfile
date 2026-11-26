FROM docker:29-cli AS dockercli
FROM jenkins/jenkins:lts-jdk21
USER root
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
USER jenkins
ARG JENKINS_MIRROR=https://ftp.halifax.rwth-aachen.de/jenkins
RUN jenkins-plugin-cli \
    --jenkins-update-center "$JENKINS_MIRROR/updates/dynamic-stable-2.580.2/update-center.actual.json" \
    --jenkins-plugin-info "$JENKINS_MIRROR/updates/current/plugin-versions.json" \
    --jenkins-update-center-download-url "$JENKINS_MIRROR/plugins" \
    --plugins workflow-aggregator github-branch-source remote-file junit credentials-binding pipeline-stage-view timestamper
