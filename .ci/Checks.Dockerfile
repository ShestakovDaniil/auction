FROM docker:29-cli AS dockercli
FROM python:3.12.16-slim-trixie
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates make mariadb-client \
    && rm -rf /var/lib/apt/lists/* \
    && install -d -o 1000 -g 1000 /pip-cache \
    && touch /pip-cache/.initialized \
    && chown 1000:1000 /pip-cache/.initialized
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose
ENV PIP_CACHE_DIR=/pip-cache PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
ENV XDG_CACHE_HOME=/pip-cache
WORKDIR /work
RUN python -m pip install --no-cache-dir pip-audit==2.10.0
