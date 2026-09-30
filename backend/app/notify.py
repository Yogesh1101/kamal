"""Send notifications: always saved to the database (the app can list them),
and pushed with Firebase Cloud Messaging when credentials are configured."""

import logging
import os

from .config import FIREBASE_CREDENTIALS
from .db import get_conn

log = logging.getLogger(__name__)

_firebase_ready = False


def init_firebase() -> None:
    global _firebase_ready
    if not FIREBASE_CREDENTIALS:
        log.warning("FIREBASE_CREDENTIALS not set: notifications will be logged, not pushed")
        return
    if not os.path.isfile(FIREBASE_CREDENTIALS):
        log.warning("Firebase key not found at %s: notifications will be logged, not pushed",
                    FIREBASE_CREDENTIALS)
        return
    import firebase_admin
    from firebase_admin import credentials

    firebase_admin.initialize_app(credentials.Certificate(FIREBASE_CREDENTIALS))
    _firebase_ready = True
    log.info("Firebase initialised")


def send(kind: str, title: str, body: str) -> bool:
    """Store the notification, then push it. Returns False if the push failed
    (the notification is still stored, so the app can list it)."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO notifications (kind, title, body) VALUES (?, ?, ?)", (kind, title, body)
        )
        tokens = [r["token"] for r in conn.execute("SELECT token FROM devices")]
    log.info("[%s] %s: %s", kind, title, body)

    if not _firebase_ready or not tokens:
        return True
    from firebase_admin import messaging

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data={"kind": kind},
        android=messaging.AndroidConfig(priority="high" if kind != "digest" else "normal"),
    )
    try:
        result = messaging.send_each_for_multicast(message)
    except Exception:
        # e.g. offline, so Google sign-in fails. Don't let one failed push stop
        # the other alerts; the caller counts the failure.
        log.exception("FCM push failed for [%s] %s", kind, title)
        return False
    dead = [tokens[i] for i, r in enumerate(result.responses)
            if not r.success and isinstance(r.exception, messaging.UnregisteredError)]
    if dead:
        # The app was uninstalled or the token changed; stop sending to it.
        with get_conn() as conn:
            conn.executemany("DELETE FROM devices WHERE token = ?", [(t,) for t in dead])
    log.info("FCM: %d sent, %d failed", result.success_count, result.failure_count)
    return result.failure_count == 0
