"""Turn a barcode into a product name and category (Open Food Facts + local cache)."""

import logging
import sqlite3

import httpx

from .config import OFF_URL, OFF_USER_AGENT

log = logging.getLogger(__name__)

# Open Food Facts category tags (without the "en:" prefix) mapped to our
# categories. Checked in this order, so put specific categories first.
CATEGORY_TAGS = [
    ("frozen", {"frozen-foods", "ice-creams"}),
    ("dairy", {"dairies", "milks", "cheeses", "yogurts", "curds", "paneer",
               "butters", "creams", "fermented-milk-products"}),
    ("bread", {"breads", "buns", "sandwich-breads"}),
    ("eggs", {"eggs", "chicken-eggs"}),
    ("meat", {"meats", "poultries", "fishes", "seafood", "chickens"}),
    ("beverages", {"beverages", "drinks", "juices", "fruit-juices", "waters",
                   "teas", "coffees", "sodas", "soft-drinks", "carbonated-drinks"}),
    ("snacks", {"snacks", "biscuits", "biscuits-and-cakes", "chips", "crisps",
                "chocolates", "confectioneries", "sweets", "namkeen"}),
    ("spices", {"spices", "herbs", "seasonings", "spice-mixes", "salts"}),
    ("condiments", {"condiments", "sauces", "pickles", "ketchup", "jams",
                    "spreads", "honeys", "oils", "vegetable-oils"}),
    ("grains", {"cereals-and-their-products", "cereals", "rices", "flours",
                "pastas", "noodles", "legumes", "pulses", "lentils",
                "breakfast-cereals", "cereal-grains"}),
    ("fruits", {"fruits", "fresh-fruits"}),
    ("vegetables", {"vegetables", "fresh-vegetables"}),
]


def map_category(tags: list[str]) -> str:
    names = {t.split(":", 1)[-1] for t in tags}
    for category, wanted in CATEGORY_TAGS:
        if names & wanted:
            return category
    return "other"


def lookup(conn: sqlite3.Connection, barcode: str) -> tuple[dict, str]:
    """Return (product, source). Source is 'cache', 'open_food_facts' or 'unknown'."""
    row = conn.execute("SELECT * FROM products WHERE barcode = ?", (barcode,)).fetchone()
    if row:
        return dict(row), "cache"

    product = _fetch_off(barcode)
    if product is None:
        # Not saved to the cache, so a later scan can try Open Food Facts again.
        return {"barcode": barcode, "name": f"Unknown product {barcode}",
                "brand": None, "category": "other", "image_url": None}, "unknown"

    conn.execute(
        "INSERT OR REPLACE INTO products (barcode, name, brand, category, image_url)"
        " VALUES (:barcode, :name, :brand, :category, :image_url)",
        product,
    )
    return product, "open_food_facts"


def _fetch_off(barcode: str) -> dict | None:
    try:
        resp = httpx.get(
            OFF_URL.format(barcode=barcode),
            params={"fields": "product_name,product_name_en,brands,categories_tags,image_front_small_url"},
            headers={"User-Agent": OFF_USER_AGENT},
            timeout=8,
        )
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("Open Food Facts lookup failed for %s: %s", barcode, exc)
        return None

    if data.get("status") != 1:
        return None
    p = data.get("product", {})
    name = p.get("product_name_en") or p.get("product_name")
    if not name:
        return None
    brand = (p.get("brands") or "").split(",")[0].strip() or None
    return {
        "barcode": barcode,
        "name": name.strip(),
        "brand": brand,
        "category": map_category(p.get("categories_tags") or []),
        "image_url": p.get("image_front_small_url"),
    }
