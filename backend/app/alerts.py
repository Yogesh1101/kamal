"""The daily expiry check, run by APScheduler (or on demand from the API).

Three kinds of alert:
- digest:  one message listing items within their category's alert window
- urgent:  one message per item on its expiry day (sent once)
- expired: one message per item the day after it expires (sent once)
"""

from datetime import date

from . import notify
from .db import get_conn
from .schemas import AlertRunOut


def run_daily_check(today: date | None = None) -> AlertRunOut:
    today = today or date.today()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT i.*, c.alert_days_before FROM items i"
            " JOIN categories c ON c.name = i.category"
            " WHERE i.status = 'active' ORDER BY i.expiry_date"
        ).fetchall()

    soon, urgent, expired = [], [], []
    for r in rows:
        days_left = (date.fromisoformat(r["expiry_date"]) - today).days
        if days_left < 0 and not r["expired_sent"]:
            expired.append(r)
        elif days_left == 0 and not r["urgent_sent"]:
            urgent.append(r)
        elif 0 < days_left <= r["alert_days_before"]:
            soon.append((r, days_left))

    push_failures = 0
    if soon:
        lines = [f"{r['name']} ({d} day{'s' if d > 1 else ''})" for r, d in soon]
        push_failures += not notify.send("digest", f"{len(soon)} item(s) expiring soon",
                                         ", ".join(lines))
    # Each item is marked right after its alert is stored, so an error later
    # in the run can't cause this alert to be sent again tomorrow.
    for r in urgent:
        push_failures += not notify.send("urgent", "Expires today!",
                                         f"Use {r['name']} today before it goes bad.")
        _mark(MARK_URGENT, r["id"])
    for r in expired:
        push_failures += not notify.send("expired", "Item expired",
                                         f"{r['name']} expired on {r['expiry_date']}. Check it and remove it.")
        _mark(MARK_EXPIRED, r["id"])

    return AlertRunOut(date=today, soon=len(soon), urgent=len(urgent), expired=len(expired),
                       push_failures=push_failures)


MARK_URGENT = "UPDATE items SET urgent_sent = 1 WHERE id = ?"
MARK_EXPIRED = "UPDATE items SET expired_sent = 1 WHERE id = ?"


def _mark(sql: str, item_id: int) -> None:
    with get_conn() as conn:
        conn.execute(sql, (item_id,))
