from datetime import date

from fastapi import APIRouter, Depends

from .. import ai_recipes
from ..db import get_conn
from ..pagination import PageParams
from ..recipes import Match, PantryItem, load_dataset, match, rank
from ..schemas import Diet, RecipeMeta, RecipePage, RecipeSuggestion, UsedItem

router = APIRouter(prefix="/recipe-suggestions", tags=["recipes"])

GOOD_ENOUGH = 3  # fewer good dataset matches than this -> ask Gemini


@router.get("", response_model=RecipePage)
def list_recipe_suggestions(diet: Diet | None = None, paging: PageParams = Depends()):
    """Recipes ranked by how much they use food that expires soon.
    Order: good dataset matches, then Gemini recipes (if needed), then other dataset matches."""
    with get_conn() as conn:
        pantry = _pantry(conn)
        dataset = rank([r for r in load_dataset() if diet in (None, r.diet)], pantry)
        good = [m for m in dataset if m.good]
        expiring = [p for p in pantry if p.expiring]

        ai_matches, ai_status = [], "not_needed"
        if len(good) < GOOD_ENOUGH and expiring:
            others = [p for p in pantry if not p.expiring and p.days_left >= 0]
            ai_list, ai_status = ai_recipes.suggest(conn, expiring, others, diet)
            ai_matches = [match(r, pantry) for r in ai_list]

    ordered = ([_out(m, "dataset") for m in good]
               + [_out(m, "gemini") for m in ai_matches]
               + [_out(m, "dataset") for m in dataset if not m.good])
    page = ordered[paging.offset:paging.offset + paging.page_size]
    return RecipePage(data=page, meta=RecipeMeta(**paging.meta(len(ordered)).model_dump(),
                                                 ai_status=ai_status))


def _pantry(conn) -> list[PantryItem]:
    today = date.today()
    rows = conn.execute(
        "SELECT i.id, i.name, i.expiry_date, c.alert_days_before FROM items i"
        " JOIN categories c ON c.name = i.category WHERE i.status = 'active'"
    ).fetchall()
    return [PantryItem(r["id"], r["name"], (date.fromisoformat(r["expiry_date"]) - today).days,
                       r["alert_days_before"]) for r in rows]


def _out(m: Match, source: str) -> RecipeSuggestion:
    r = m.recipe
    return RecipeSuggestion(
        name=r.name, source=source, score=m.score, good_match=m.good, coverage=m.coverage,
        used_items=[UsedItem(id=p.id, name=p.name, days_left=p.days_left) for p in m.used],
        missing_ingredients=m.missing, ingredients=list(r.ingredients), steps=list(r.steps),
        diet=r.diet, course=r.course, total_time_minutes=r.total_time_minutes,
    )
