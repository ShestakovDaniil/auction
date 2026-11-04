"""First-run configuration must work against a normal MariaDB/MySQL server."""

import stat

from dotenv import dotenv_values
import pytest
from sqlalchemy.engine.url import make_url

from scripts import setup_env


def configure(monkeypatch, tmp_path, answers, password="A-secret%@with-special-characters"):
    env_file = tmp_path / ".env"
    monkeypatch.setattr(setup_env, "ENV_FILE", env_file)
    provided = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(provided))
    monkeypatch.setattr(setup_env, "getpass", lambda _prompt: password)
    return env_file


def test_initial_setup_uses_standard_mariadb_port_and_isolated_db(monkeypatch, tmp_path):
    env_file = configure(monkeypatch, tmp_path, ["", "", "", ""])
    setup_env.main()

    values = dotenv_values(env_file)
    app_url = make_url(values["DATABASE_URL"])
    test_url = make_url(values["TEST_DATABASE_URL"])
    assert (app_url.host, app_url.port, app_url.database) == ("127.0.0.1", 3306, "auction_lab")
    assert (test_url.host, test_url.port, test_url.database) == ("127.0.0.1", 3306, "auction_lab_test")
    assert app_url.password == "A-secret%@with-special-characters"
    assert test_url.password == app_url.password
    assert len(values["APP_SECRET_KEY"]) >= 32
    assert values["AUTO_CREATE_TABLES"] == "false"
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert all(not name.startswith("MARIADB_") for name in values)


def test_setup_accepts_a_separate_database_server(monkeypatch, tmp_path):
    env_file = configure(monkeypatch, tmp_path, ["labuser", "172.16.10.20", "3306", "school_auction"])
    setup_env.main()
    values = dotenv_values(env_file)
    url = make_url(values["DATABASE_URL"])
    assert (url.username, url.host, url.database) == ("labuser", "172.16.10.20", "school_auction")
    assert make_url(values["TEST_DATABASE_URL"]).database == "school_auction_test"


def test_setup_never_overwrites_an_existing_env(monkeypatch, tmp_path):
    env_file = configure(monkeypatch, tmp_path, [])
    env_file.write_text("KEEP_EXISTING=true\n")
    setup_env.main()
    assert env_file.read_text() == "KEEP_EXISTING=true\n"


@pytest.mark.parametrize(
    ("answers", "password", "error"),
    [
        (["", "", "", ""], "", "Пароль"),
        (["", "", "0", ""], "nonempty", "порт"),
        (["", "", "3306", "bad-db"], "nonempty", "имя базы"),
        (["", "bad host", "3306", ""], "nonempty", "хост"),
    ],
)
def test_setup_rejects_invalid_connection_settings(monkeypatch, tmp_path, answers, password, error):
    env_file = configure(monkeypatch, tmp_path, answers, password=password)
    with pytest.raises(SystemExit, match=error):
        setup_env.main()
    assert not env_file.exists()
