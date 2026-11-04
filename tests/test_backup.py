from pathlib import Path
import stat

import pytest

from scripts.db_backup import connection_options, parse_db, restore_database


def test_only_mysql_urls_with_safe_database_names_allowed():
    url = "mysql+pymysql://auction:secret@127.0.0.1:3306/auction_lab"
    assert parse_db(url).database == "auction_lab"
    with pytest.raises(ValueError):
        parse_db("sqlite:///not_mariadb.db")
    with pytest.raises(ValueError):
        parse_db("mysql+pymysql://auction:secret@localhost/bad-db")
    with pytest.raises(ValueError):
        parse_db("mysql+pymysql://auction@localhost/auction_lab")


def test_options_file_is_private_and_ephemeral():
    url = "mysql+pymysql://auction:Pa%24%24word@127.0.0.1:3306/auction_lab"
    with connection_options(url) as (parsed, file_path):
        assert stat.S_IMODE(file_path.stat().st_mode) == 0o600
        data = file_path.read_text()
        assert 'password="Pa$$word"' in data
        assert 'user="auction"' in data
        assert parsed.database == "auction_lab"
    assert not file_path.exists()


def test_restore_needs_explicit_matching_database_name(tmp_path: Path):
    url = "mysql+pymysql://auction:secret@127.0.0.1:3306/auction_lab"
    with pytest.raises(ValueError, match="CONFIRM_RESTORE"):
        restore_database(url, tmp_path / "anything.sql.gz", "wrong")
    with pytest.raises(ValueError, match="BACKUP_FILE"):
        restore_database(url, tmp_path / "anything.sql.gz", "auction_lab")
