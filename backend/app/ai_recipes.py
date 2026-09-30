"""Gemini fallback: asks for recipes when the dataset has fewer than 3 good
matches. Answers are cached in SQLite, keyed by the expiring items, so the
same situation never calls the API twice."""

import json
import logging
import sqlite3
from typing import Literal

from pydantic import BaseModel

from .config import GEMINI_API_KEY, GEMINI_MODELS
from .recipes import PantryItem, Recipe

log = logging.getLogger(__name__)

AiStatus = Literal["not_needed", "cached", "generated", "unavailable"]


class AiRecipe(BaseModel):
    """The JSON shape Gemini is told to return."""
    name: str
    ingredients: list[str]
    steps: list[str]
    total_time_minutes: int
    diet: str


def suggest(conn: sqlite3.Connection, expiring: list[PantryItem], others: list[PantryItem],
            diet: str | None) -> tuple[list[Recipe], AiStatus]:
    key = _cache_key(expiring, diet)
    row = conn.execute("SELECT recipes_json FROM ai_recipes WHERE cache_key = ?", (key,)).fetchone()
    if row:
        return [_to_recipe(AiRecipe(**r)) for r in json.loads(row["recipes_json"])], "cached"

    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY not set: no AI recipe fallback")
        return [], "unavailable"

    from google.genai import errors

    # The dataset results are returned either way; if every model fails the
    # app sees aiStatus "unavailable".
    for model in GEMINI_MODELS:
        try:
            answer = _ask_gemini(model, expiring, others, diet)
        except errors.APIError as exc:
            log.warning("Gemini %s failed: %s %s", model, exc.code, exc.message)
            if exc.code in (400, 401, 403):
                return [], "unavailable"  # bad key or bad request: other models won't help
            continue                      # busy, over quota or model retired: try the next one
        except Exception:
            log.exception("Gemini %s request failed", model)
            continue
        conn.execute("INSERT OR REPLACE INTO ai_recipes (cache_key, model, recipes_json) VALUES (?, ?, ?)",
                     (key, model, json.dumps([r.model_dump() for r in answer])))
        log.info("Gemini %s suggested %d recipes", model, len(answer))
        return [_to_recipe(r) for r in answer], "generated"
    return [], "unavailable"


def _cache_key(expiring: list[PantryItem], diet: str | None) -> str:
    names = sorted({" ".join(i.name.lower().split()) for i in expiring})
    return f"{diet or 'any'}|{'|'.join(names)}"


def _ask_gemini(model: str, expiring: list[PantryItem], others: list[PantryItem],
                diet: str | None) -> list[AiRecipe]:
    from google import genai
    from google.genai import types

    def describe(item: PantryItem) -> str:
        when = "today" if item.days_left == 0 else f"in {item.days_left} day(s)"
        return f"- {item.name} (expires {when})"

    prompt = "\n".join([
        "You help an Indian household avoid food waste.",
        "Suggest 3 Indian home-style recipes that use as many of these soon-to-expire items as possible:",
        *[describe(i) for i in expiring],
        "Other food in the kitchen: " + (", ".join(i.name for i in others) or "none") + ".",
        "Assume common pantry staples (salt, oil, sugar, everyday spices) are available.",
        "Only vegetarian recipes." if diet == "vegetarian" else "",
        "Only non-vegetarian recipes." if diet == "non vegetarian" else "",
        "Use plain ingredient names (e.g. 'milk', 'curd', 'tomato'), at most 8 short steps per recipe,",
        "and set diet to 'vegetarian' or 'non vegetarian'.",
    ])
    client = genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(timeout=30_000))
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[AiRecipe],
            temperature=0.7,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    if not response.parsed:
        raise ValueError(f"Gemini returned no usable recipes: {response.text!r:.200}")
    return response.parsed


def _to_recipe(r: AiRecipe) -> Recipe:
    return Recipe(name=r.name, ingredients=tuple(r.ingredients), steps=tuple(r.steps),
                  diet="vegetarian" if r.diet.strip().lower() == "vegetarian" else "non vegetarian",
                  course=None, total_time_minutes=r.total_time_minutes)
