"""Database connection and small helpers shared by the other modules."""

import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


class BankError(Exception):
    """Raised for invalid input or a business rule being broken."""


def _config():
    # Read at call time so tests can point to a different database.
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "bank_system"),
    }


def get_connection():
    try:
        return mysql.connector.connect(**_config())
    except mysql.connector.Error as err:
        raise BankError(f"Could not connect to the database: {err}") from err


@contextmanager
def db_transaction():
    """Open a connection, commit on success, roll back on any error.

    Everything done inside one `with db_transaction() as conn:` block is a
    single unit of work: either all of it is saved, or none of it.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute(conn, sql, params=()):
    """Run an INSERT/UPDATE/DELETE on an open connection; returns last insert id."""
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid
    finally:
        cursor.close()


def _query(sql, params, conn, only_one):
    own_connection = conn is None
    if own_connection:
        conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(sql, params)
        result = cursor.fetchone() if only_one else cursor.fetchall()
        cursor.close()
        return result
    finally:
        if own_connection:
            conn.commit()
            conn.close()


def fetch_one(sql, params=(), conn=None):
    """Return the first row as a dict, or None."""
    return _query(sql, params, conn, only_one=True)


def fetch_all(sql, params=(), conn=None):
    """Return all rows as a list of dicts."""
    return _query(sql, params, conn, only_one=False)
