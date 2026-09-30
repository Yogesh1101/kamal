"""Settings read from environment variables (or a backend/.env file)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "kitchen.db"))

# Path to the Firebase service-account JSON (relative paths are from backend/).
# When unset, notifications are only logged and stored, not pushed.
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "")
if FIREBASE_CREDENTIALS:
    FIREBASE_CREDENTIALS = str(BASE_DIR / FIREBASE_CREDENTIALS)

TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
DIGEST_HOUR = int(os.getenv("DIGEST_HOUR", "8"))
DIGEST_MINUTE = int(os.getenv("DIGEST_MINUTE", "0"))

OFF_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
OFF_USER_AGENT = "SmartKitchenInventory/0.1 (academic project)"
