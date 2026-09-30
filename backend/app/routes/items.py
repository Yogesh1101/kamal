from fastapi import APIRouter, Depends, Request, Response

from .. import inventory
from ..db import get_conn
from ..pagination import PageParams
from ..schemas import Envelope, ItemCreate, ItemOut, ItemUpdate, Page, Status

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=Page[ItemOut])
def list_items(status: Status = "active", paging: PageParams = Depends()):
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM items WHERE status = ?", (status,)).fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM items WHERE status = ? ORDER BY expiry_date, id LIMIT ? OFFSET ?",
            (status, paging.page_size, paging.offset),
        ).fetchall()
        return Page(data=[inventory.to_item_out(r) for r in rows], meta=paging.meta(total))


@router.post("", response_model=Envelope[ItemOut], status_code=201)
def create_item(data: ItemCreate, request: Request, response: Response):
    with get_conn() as conn:
        item = inventory.add_item(conn, data)
    response.headers["Location"] = str(request.url_for("read_item", item_id=item.id))
    return Envelope(data=item)


@router.get("/{item_id}", response_model=Envelope[ItemOut])
def read_item(item_id: int):
    with get_conn() as conn:
        return Envelope(data=inventory.to_item_out(inventory.get_item(conn, item_id)))


@router.patch("/{item_id}", response_model=Envelope[ItemOut])
def update_item(item_id: int, data: ItemUpdate):
    with get_conn() as conn:
        return Envelope(data=inventory.update_item(conn, item_id, data))


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int):
    with get_conn() as conn:
        inventory.get_item(conn, item_id)
        conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
