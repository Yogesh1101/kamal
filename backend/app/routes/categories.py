from fastapi import APIRouter, Depends

from ..db import get_conn
from ..inventory import get_category
from ..pagination import PageParams
from ..schemas import CategoryOut, CategoryUpdate, Envelope, Page

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=Page[CategoryOut])
def list_categories(paging: PageParams = Depends()):
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        rows = conn.execute("SELECT * FROM categories ORDER BY name LIMIT ? OFFSET ?",
                            (paging.page_size, paging.offset)).fetchall()
        return Page(data=[CategoryOut(**r) for r in rows], meta=paging.meta(total))


@router.patch("/{name}", response_model=Envelope[CategoryOut])
def update_category(name: str, data: CategoryUpdate):
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    with get_conn() as conn:
        category = {**dict(get_category(conn, name)), **changes}
        conn.execute(
            "UPDATE categories SET shelf_life_days = :shelf_life_days,"
            " alert_days_before = :alert_days_before WHERE name = :name",
            category,
        )
        return Envelope(data=CategoryOut(**get_category(conn, name)))
