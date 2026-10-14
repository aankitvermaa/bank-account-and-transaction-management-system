"""Test setup: builds a separate test database so real data is never touched."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEST_DB = "bank_system_test"
os.environ["DB_NAME"] = TEST_DB  # must be set before database.py reads config

import mysql.connector  # noqa: E402
import pytest  # noqa: E402

from database import _config  # noqa: E402


def _server_connection():
    cfg = _config()
    cfg.pop("database")
    return mysql.connector.connect(**cfg)


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Create the test database from the project's SQL file."""
    sql = (ROOT / "database" / "bank_system.sql").read_text()
    sql = sql.replace("bank_system", TEST_DB)
    lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]

    conn = _server_connection()
    cursor = conn.cursor()
    for statement in statements:
        cursor.execute(statement)
    conn.commit()
    conn.close()
    yield


@pytest.fixture(autouse=True)
def clean_tables(test_database):
    """Empty all tables before each test so tests do not affect each other."""
    conn = mysql.connector.connect(**_config())
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in ("transfers", "transactions", "accounts", "customers"):
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    conn.close()
    yield
