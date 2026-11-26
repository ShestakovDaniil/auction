# Fixed Python patch version. Do not use floating tags such as 'latest'.
FROM python:3.12.16-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /opt/auction

# The existing Lab 3 backup/restore scripts need the MariaDB client.
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends mariadb-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir pip==26.3 \
    && python -m pip install --no-cache-dir -r requirements.txt

RUN groupadd --system --gid 10001 auction \
    && useradd --system --uid 10001 --gid 10001 --home-dir /opt/auction --no-create-home auction \
    && mkdir -p /opt/auction/backups \
    && chown auction:auction /opt/auction/backups

COPY --chown=auction:auction app/ ./app/
COPY --chown=auction:auction alembic/ ./alembic/
COPY --chown=auction:auction alembic.ini ./
COPY --chown=auction:auction scripts/ ./scripts/

USER 10001:10001
EXPOSE 8000

# Exec-form command makes Uvicorn the main process and lets it receive SIGTERM.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "15"]
