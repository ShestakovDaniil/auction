"""Policy tests run without Docker; the full live test is make container-check on Linux."""

from pathlib import Path

import pytest

from scripts import container_check


def test_current_docker_policy():
    container_check.static_policy()


def test_compose_rejects_database_port():
    valid = {
        "services": {
            "db": {
                "image": "mariadb:11.4.12",
                "healthcheck": {"test": ["CMD", "true"]},
                "cpus": 1,
                "mem_limit": "1g",
                "networks": {"backend": None},
                "volumes": [{"target": "/var/lib/mysql", "type": "volume"}],
                "ports": [{"target": 3306}],
            },
            "migrate": {
                "image": "auction-lab:lab4",
                "cpus": 1,
                "mem_limit": "384m",
                "networks": {"backend": None},
                "depends_on": {"db": {"condition": "service_healthy"}},
            },
            "app": {
                "image": "auction-lab:lab4",
                "healthcheck": {"test": ["CMD", "true"]},
                "cpus": 1,
                "mem_limit": "512m",
                "networks": {"backend": None},
                "ports": [{"host_ip": "127.0.0.1", "target": 8000}],
                "depends_on": {"migrate": {"condition": "service_completed_successfully"}},
                "environment": {"DATABASE_URL": "mysql+pymysql://auction_app:secret@db:3306/auction_lab", "AUTO_CREATE_TABLES": "false"},
            },
        }
    }
    with pytest.raises(container_check.CheckError, match="публиковать порт БД"):
        container_check.check_compose(valid)
    valid["services"]["db"].pop("ports")
    container_check.check_compose(valid)


def test_example_secrets_are_not_accepted(monkeypatch, tmp_path: Path):
    template = container_check.ROOT / ".env.container.example"
    file = tmp_path / ".env.container"
    file.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(container_check, "ENV_FILE", file)
    with pytest.raises(container_check.CheckError):
        container_check.load_env()


def test_policy_rejects_root_user(monkeypatch, tmp_path: Path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text((container_check.ROOT / "Dockerfile").read_text(encoding="utf-8").replace("USER 10001:10001", "USER root:root"), encoding="utf-8")
    monkeypatch.setattr(container_check, "DOCKERFILE", dockerfile)
    with pytest.raises(container_check.CheckError, match="непривилегированного"):
        container_check.static_policy()
