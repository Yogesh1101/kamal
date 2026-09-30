from fastapi import APIRouter, Depends

from ..alerts import run_daily_check
from ..db import get_conn, local_timestamp
from ..pagination import PageParams
from ..schemas import (AlertRunIn, AlertRunOut, DeviceIn, DeviceOut, Envelope,
                       NotificationOut, Page)

router = APIRouter(tags=["alerts"])


@router.post("/devices", response_model=Envelope[DeviceOut], status_code=201)
def register_device(data: DeviceIn):
    """The app sends its FCM token here on start-up. Sending the same token again is harmless.
    No Location header: there's no per-device endpoint, and tokens shouldn't appear in URLs (logs)."""
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO devices (token) VALUES (?)", (data.token,))
        row = conn.execute("SELECT * FROM devices WHERE token = ?", (data.token,)).fetchone()
    return Envelope(data=DeviceOut(token=row["token"], created_at=local_timestamp(row["created_at"])))


@router.get("/notifications", response_model=Page[NotificationOut])
def list_notifications(paging: PageParams = Depends()):
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        rows = conn.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ? OFFSET ?",
                            (paging.page_size, paging.offset)).fetchall()
    data = [NotificationOut(**{**dict(r), "created_at": local_timestamp(r["created_at"])})
            for r in rows]
    return Page(data=data, meta=paging.meta(total))


@router.post("/alert-runs", response_model=Envelope[AlertRunOut])
def create_alert_run(data: AlertRunIn | None = None):
    """Run the daily check now. Send {"today": "YYYY-MM-DD"} to pretend it's another day (demos).
    Returns 200, not 201: a run isn't stored, so there's nothing to fetch later."""
    return Envelope(data=run_daily_check(data.today if data else None))
