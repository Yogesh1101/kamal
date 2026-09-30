"""SQLite connection, table creation and seed data."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import DB_PATH, TIMEZONE

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    name              TEXT PRIMARY KEY,
    shelf_life_days   INTEGER NOT NULL,
    alert_days_before INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    barcode    TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    brand      TEXT,
    category   TEXT NOT NULL REFERENCES categories(name),
    image_url  TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode        TEXT,
    name           TEXT NOT NULL,
    brand          TEXT,
    category       TEXT NOT NULL REFERENCES categories(name),
    quantity       INTEGER NOT NULL DEFAULT 1,
    added_on       TEXT NOT NULL,
    expiry_date    TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'active',
    urgent_sent    INTEGER NOT NULL DEFAULT 0,
    expired_sent   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS devices (
    token      TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS ai_recipes (
    cache_key    TEXT PRIMARY KEY,
    model        TEXT NOT NULL,
    recipes_json TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT NOT NULL,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# (category, default shelf life in days, alert this many days before expiry)
DEFAULT_CATEGORIES = [
    ("dairy", 5, 2),
    ("bread", 4, 1),
    ("batter", 3, 1),
    ("eggs", 21, 3),
    ("meat", 2, 1),
    ("fruits", 5, 2),
    ("vegetables", 5, 2),
    ("beverages", 180, 14),
    ("snacks", 90, 7),
    ("grains", 180, 14),
    ("spices", 365, 30),
    ("condiments", 180, 14),
    ("frozen", 90, 7),
    ("other", 30, 3),
]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    """Open a connection, commit on success, roll back on error, always close."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def local_timestamp(value: str) -> datetime:
    """SQLite stores local time without a zone; attach it so the API sends
    an unambiguous ISO 8601 time such as 2026-09-30T16:21:44+05:30."""
    return datetime.fromisoformat(value).replace(tzinfo=ZoneInfo(TIMEZONE))


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT OR IGNORE INTO categories VALUES (?, ?, ?)", DEFAULT_CATEGORIES
        )
