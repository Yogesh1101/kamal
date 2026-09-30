"""FastAPI entry point. Run from backend/:  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --reload"""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, FastAPI

from . import errors, notify
from .alerts import run_daily_check
from .config import DIGEST_HOUR, DIGEST_MINUTE, TIMEZONE
from .db import init_db
from .routes import alerts, categories, items, recipes, scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at start-up (before yield) and once at shutdown (after yield).
    init_db()
    notify.init_firebase()
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(run_daily_check, CronTrigger(hour=DIGEST_HOUR, minute=DIGEST_MINUTE),
                      id="daily_check", misfire_grace_time=3600)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Smart Kitchen Inventory", lifespan=lifespan)
errors.install(app)

api = APIRouter(prefix=API_PREFIX)
api.include_router(items.router)
api.include_router(categories.router)
api.include_router(scan.router)
api.include_router(alerts.router)
api.include_router(recipes.router)


@api.get("/health", tags=["health"])
def health():
    return {"data": {"status": "ok"}}


app.include_router(api)
