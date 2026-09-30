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

RECIPES_CSV = Path(os.getenv("RECIPES_CSV", BASE_DIR / "data" / "indian_food.csv"))

# Gemini is only used when the dataset has fewer than 3 good recipes.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Tried in order: when a model is busy, over quota or retired, the next one is used.
GEMINI_MODELS = [m.strip() for m in os.getenv(
    "GEMINI_MODELS", "gemini-3.8-flash,gemini-3.5-flash,gemini-3.1-flash-lite").split(",") if m.strip()]

OFF_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
OFF_USER_AGENT = "SmartKitchenInventory/0.1 (academic project)"
