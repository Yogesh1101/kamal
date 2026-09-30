"""Inventory rules shared by the API routes and the scan flow."""

import sqlite3
from datetime import date, timedelta

from .errors import invalid, not_found
from .schemas import ItemCreate, ItemOut, ItemUpdate

# Columns that may be cleared by sending null; the rest are NOT NULL.
NULLABLE = {"brand"}


def to_item_out(row: sqlite3.Row, today: date | None = None) -> ItemOut:
    today = today or date.today()
    expiry = date.fromisoformat(row["expiry_date"])
    return ItemOut(**{k: row[k] for k in row.keys() if k in ItemOut.model_fields},
                   days_left=(expiry - today).days)


def get_category(conn: sqlite3.Connection, name: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM categories WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise not_found(f"Category '{name}'")
    return row


def check_category(conn: sqlite3.Connection, name: str) -> sqlite3.Row:
    """Like get_category, but for a category named in a request body (400, not 404)."""
    row = conn.execute("SELECT * FROM categories WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise invalid("category", f"unknown category '{name}'")
    return row


def get_item(conn: sqlite3.Connection, item_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise not_found(f"Item {item_id}")
    return row


def add_item(conn: sqlite3.Connection, data: ItemCreate) -> ItemOut:
    category = check_category(conn, data.category)
    today = date.today()
    expiry = data.expiry_date or today + timedelta(days=category["shelf_life_days"])
    cur = conn.execute(
        "INSERT INTO items (barcode, name, brand, category, quantity, added_on, expiry_date)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data.barcode, data.name, data.brand, data.category, data.quantity,
         today.isoformat(), expiry.isoformat()),
    )
    return to_item_out(get_item(conn, cur.lastrowid), today)


def update_item(conn: sqlite3.Connection, item_id: int, data: ItemUpdate) -> ItemOut:
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items()
               if v is not None or k in NULLABLE}
    if "category" in changes:
        check_category(conn, changes["category"])
    if "expiry_date" in changes:
        changes["expiry_date"] = changes["expiry_date"].isoformat()
        # New date, so the expiry-day and expired alerts can fire again.
        changes["urgent_sent"] = 0
        changes["expired_sent"] = 0

    # Apply the changes to the stored row, then write every editable column
    # back with one fixed statement (no SQL built from strings).
    item = {**dict(get_item(conn, item_id)), **changes}
    conn.execute(
        "UPDATE items SET name = :name, brand = :brand, category = :category,"
        " quantity = :quantity, expiry_date = :expiry_date, status = :status,"
        " urgent_sent = :urgent_sent, expired_sent = :expired_sent WHERE id = :id",
        item,
    )
    return to_item_out(get_item(conn, item_id))
