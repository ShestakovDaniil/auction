from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.db import Base
from app import models  # noqa: F401


def test_all_tables_compile_for_mysql_dialect():
    dialect = mysql.dialect()
    statements = [str(CreateTable(table).compile(dialect=dialect)) for table in Base.metadata.sorted_tables]
    assert len(statements) == 4
    joined = "\n".join(statements)
    assert "CREATE TABLE users" in joined
    assert "CREATE TABLE lots" in joined
    assert "CREATE TABLE auctions" in joined
    assert "CREATE TABLE sales" in joined
