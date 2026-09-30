"""Shapes of the JSON the API accepts and returns (validated by Pydantic).

Python code uses snake_case; the JSON uses camelCase (e.g. expiry_date <-> expiryDate).
Every response is wrapped: {"data": ...} or, for lists, {"data": [...], "meta": {...}}.
"""

from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Status = Literal["active", "consumed", "discarded"]
T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PageMeta(ApiModel):
    page: int
    page_size: int
    total_pages: int
    total_count: int


class Envelope(ApiModel, Generic[T]):
    data: T


class Page(ApiModel, Generic[T]):
    data: list[T]
    meta: PageMeta


class ItemCreate(ApiModel):
    name: str = Field(min_length=1)
    category: str = "other"
    brand: str | None = None
    barcode: str | None = None
    quantity: int = Field(default=1, ge=1)
    expiry_date: date | None = None  # None: use the category's shelf life


class ItemUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1)
    category: str | None = None
    brand: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    expiry_date: date | None = None
    status: Status | None = None


class ItemOut(ApiModel):
    id: int
    barcode: str | None
    name: str
    brand: str | None
    category: str
    quantity: int
    added_on: date
    expiry_date: date
    days_left: int
    status: Status


class CategoryOut(ApiModel):
    name: str
    shelf_life_days: int
    alert_days_before: int


class CategoryUpdate(ApiModel):
    shelf_life_days: int | None = Field(default=None, ge=1)
    alert_days_before: int | None = Field(default=None, ge=0)


class CodeIn(ApiModel):
    code: str = Field(min_length=1)


class ScanOut(ApiModel):
    code: str
    source: Literal["cache", "open_food_facts", "label", "unknown"]
    item: ItemOut


class DeviceIn(ApiModel):
    token: str = Field(min_length=1)


class DeviceOut(ApiModel):
    token: str
    created_at: datetime


class NotificationOut(ApiModel):
    id: int
    kind: str
    title: str
    body: str
    created_at: datetime


Diet = Literal["vegetarian", "non vegetarian"]


class UsedItem(ApiModel):
    id: int
    name: str
    days_left: int


class RecipeSuggestion(ApiModel):
    name: str
    source: Literal["dataset", "gemini"]
    score: float
    good_match: bool
    coverage: float
    used_items: list[UsedItem]
    missing_ingredients: list[str]
    ingredients: list[str]
    steps: list[str]  # empty for dataset recipes (the dataset has no steps)
    diet: Diet
    course: str | None
    total_time_minutes: int | None


class RecipeMeta(PageMeta):
    # not_needed: 3+ good dataset matches (or nothing expiring); cached/generated:
    # Gemini recipes included; unavailable: Gemini was needed but failed.
    ai_status: Literal["not_needed", "cached", "generated", "unavailable"]


class RecipePage(ApiModel):
    data: list[RecipeSuggestion]
    meta: RecipeMeta


class AlertRunIn(ApiModel):
    today: date | None = None  # pretend it's another day (for demos)


class AlertRunOut(ApiModel):
    date: date
    soon: int
    urgent: int
    expired: int
    push_failures: int
