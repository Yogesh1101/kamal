"""Recipe suggestions from the Indian Food 101 dataset, ranked by how much
they use food that is about to expire.

Scoring, per recipe:
  urgency  = sum over the inventory items it uses (each item counted once):
             expires today 5, in 1 day 4, in 2 days 3, within its alert window 2, later 1
             (expired items are never suggested)
  coverage = share of its ingredients you have (in the inventory, or a pantry staple)
  score    = urgency x coverage
A recipe is a "good match" when it uses at least one item inside its alert
window and coverage is at least 50%.
"""

import csv
import re
from dataclasses import dataclass
from functools import cache

from .config import RECIPES_CSV

GOOD_COVERAGE = 0.5

# Words that don't change what the ingredient is.
FILLER = {"powder", "fresh", "grated", "chopped", "dried", "whole", "raw", "boiled",
          "ripe", "sliced", "ground", "paste", "of", "and", "a", "the", "for", "some"}

# Everyday names and spellings -> one canonical name, so "Amul Masti Dahi"
# matches the ingredient "yogurt".
SYNONYMS = {
    "dahi": "curd", "yogurt": "curd", "yoghurt": "curd",
    "atta": "wheat flour", "maida flour": "maida", "all purpose flour": "maida",
    "plain flour": "maida", "besan": "gram flour", "bengal gram flour": "gram flour",
    "clarified butter": "ghee", "sooji": "semolina", "suji": "semolina", "rava": "semolina",
    "aloo": "potato", "pyaz": "onion", "tamatar": "tomato", "chawal": "rice",
    "chilli": "chili", "chilly": "chili", "capsicum": "bell pepper",
}

# Assumed to be in every Indian kitchen, so they count as "have" for coverage.
STAPLES = ["salt", "sugar", "oil", "water", "ghee", "turmeric", "chili", "red chili",
           "garam masala", "cumin", "cumin seed", "mustard seed", "curry leave", "asafoetida",
           "hing", "coriander", "baking soda", "jaggery", "cardamom", "black pepper",
           "fenugreek seed", "bay leaf", "clove", "cinnamon"]


def _singular(word: str) -> str:
    if word.endswith("oes"):
        return word[:-2]                      # tomatoes -> tomato
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"                # chillies -> chilly
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]                      # carrots -> carrot
    return word


_SYNONYM_RE = [(re.compile(rf"\b{re.escape(k)}\b"), v)
               for k, v in sorted(SYNONYMS.items(), key=lambda kv: -len(kv[0]))]


def tokens(text: str) -> frozenset[str]:
    """'Grated Coconut' -> {'coconut'}; 'Amul Masti Dahi' -> {'amul', 'masti', 'curd'}."""
    words = re.sub(r"[^a-z]+", " ", text.lower()).split()
    phrase = " ".join(_singular(w) for w in words)
    for pattern, canonical in _SYNONYM_RE:
        phrase = pattern.sub(canonical, phrase)
    return frozenset(w for w in phrase.split() if w not in FILLER)


STAPLE_TOKENS = {tokens(s) for s in STAPLES}


@dataclass(frozen=True)
class Recipe:
    name: str
    ingredients: tuple[str, ...]
    diet: str
    course: str | None
    total_time_minutes: int | None
    steps: tuple[str, ...] = ()


@dataclass(frozen=True)
class PantryItem:
    id: int
    name: str
    days_left: int
    alert_days_before: int

    @property
    def expiring(self) -> bool:
        return 0 <= self.days_left <= self.alert_days_before


@dataclass
class Match:
    recipe: Recipe
    used: list[PantryItem]
    missing: list[str]
    coverage: float
    score: float

    @property
    def good(self) -> bool:
        return any(i.expiring for i in self.used) and self.coverage >= GOOD_COVERAGE


def urgency(item: PantryItem) -> int:
    if item.days_left < 0:
        return 0
    if item.days_left <= 2:
        return 5 - item.days_left
    return 2 if item.expiring else 1


def match(recipe: Recipe, pantry: list[PantryItem]) -> Match:
    usable = [(p, tokens(p.name)) for p in pantry if p.days_left >= 0]
    used: dict[int, PantryItem] = {}
    missing = []
    for ingredient in recipe.ingredients:
        need = tokens(ingredient)
        if not need:
            continue
        hits = [p for p, have in usable if need <= have]
        if hits:
            best = max(hits, key=urgency)        # use the item closest to expiry first
            used[best.id] = best
        elif need not in STAPLE_TOKENS:
            missing.append(ingredient)
    total = len(recipe.ingredients) or 1
    coverage = (total - len(missing)) / total
    score = sum(urgency(p) for p in used.values()) * coverage
    return Match(recipe, sorted(used.values(), key=lambda p: p.days_left), missing,
                 round(coverage, 2), round(score, 2))


def rank(recipes: list[Recipe], pantry: list[PantryItem]) -> list[Match]:
    """Recipes that use at least one inventory item, best first."""
    matches = [m for m in (match(r, pantry) for r in recipes) if m.used]
    return sorted(matches, key=lambda m: (m.good, m.score), reverse=True)


@cache
def load_dataset() -> tuple[Recipe, ...]:
    def minutes(value: str) -> int | None:
        return int(value) if value.strip().lstrip("-").isdigit() and int(value) >= 0 else None

    with open(RECIPES_CSV, newline="", encoding="utf-8") as f:
        recipes = []
        for row in csv.DictReader(f):
            prep, cook = minutes(row["prep_time"]), minutes(row["cook_time"])
            recipes.append(Recipe(
                name=row["name"].strip(),
                ingredients=tuple(i.strip() for i in row["ingredients"].split(",") if i.strip()),
                diet="vegetarian" if row["diet"].strip() == "vegetarian" else "non vegetarian",
                course=row["course"].strip() if row["course"].strip() not in ("", "-1") else None,
                total_time_minutes=(prep or 0) + (cook or 0) if prep is not None or cook is not None else None,
            ))
    return tuple(recipes)
