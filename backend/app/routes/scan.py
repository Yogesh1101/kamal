"""Scan endpoints. Every scan adds one item with a default expiry date,
which the user can then correct in the app."""

import json
import re

from fastapi import APIRouter, File, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool

from ..barcode import decode_image
from ..config import MAX_IMAGE_BYTES
from ..db import get_conn
from ..errors import ApiError, invalid
from ..inventory import add_item
from ..products import lookup
from ..schemas import CodeIn, Envelope, ItemCreate, ScanOut

router = APIRouter(prefix="/scans", tags=["scans"])

# Home-made/loose items carry a printed QR label: "SKI:" + JSON,
# e.g. SKI:{"name": "Idli batter", "category": "batter"}
LABEL_PREFIX = "SKI:"

# Product barcodes are all digits: EAN-8, UPC-A (12), EAN-13 or GTIN-14.
# Anything else (a UPI payment QR, a website link) is not a product.
BARCODE = re.compile(r"\d{8,14}")


@router.post("/images", response_model=Envelope[ScanOut], status_code=201)
async def scan_upload(request: Request, response: Response, image: UploadFile = File(...)):
    """Photo sent as a form upload (simulated scanner, /docs page)."""
    if image.size is not None and image.size > MAX_IMAGE_BYTES:
        raise _too_large()
    return await _scan_image(await image.read(), request, response)


@router.post("/jpeg", response_model=Envelope[ScanOut], status_code=201)
async def scan_jpeg(request: Request, response: Response):
    """Photo sent as the raw request body (Content-Type: image/jpeg). Easier for the ESP32-CAM."""
    return await _scan_image(await _read_body_limited(request), request, response)


@router.post("/codes", response_model=Envelope[ScanOut], status_code=201)
def scan_code(data: CodeIn, request: Request, response: Response):
    """Barcode text typed in or read by another device; skips image decoding."""
    return _created(_add_from_code(data.code.strip()), request, response)


def _too_large() -> ApiError:
    return ApiError(413, "PAYLOAD_TOO_LARGE",
                    f"Image is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB")


async def _read_body_limited(request: Request) -> bytes:
    """Read the raw body, stopping as soon as it passes the size limit
    (also covers requests that don't state a Content-Length)."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_IMAGE_BYTES:
        raise _too_large()
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_IMAGE_BYTES:
            raise _too_large()
    return bytes(body)


async def _scan_image(image_bytes: bytes, request: Request, response: Response) -> Envelope[ScanOut]:
    if not image_bytes:
        raise invalid("image", "empty image")
    try:
        # Decoding is CPU work, so run it off the event loop.
        code = await run_in_threadpool(decode_image, image_bytes)
    except ValueError as exc:
        raise invalid("image", str(exc)) from exc
    if code is None:
        raise ApiError(422, "NO_CODE_FOUND", "No barcode or QR code found in the image")
    return _created(await run_in_threadpool(_add_from_code, code), request, response)


def _created(scan: ScanOut, request: Request, response: Response) -> Envelope[ScanOut]:
    response.headers["Location"] = str(request.url_for("read_item", item_id=scan.item.id))
    return Envelope(data=scan)


def _add_from_code(code: str) -> ScanOut:
    if code.startswith(LABEL_PREFIX):
        try:
            label = json.loads(code[len(LABEL_PREFIX):])
            data = ItemCreate(name=label["name"], category=label.get("category", "other"))
        except (ValueError, KeyError, TypeError) as exc:
            raise ApiError(400, "INVALID_LABEL", f"Bad kitchen QR label: {exc}") from exc
        with get_conn() as conn:
            return ScanOut(code=code, source="label", item=add_item(conn, data))

    if not BARCODE.fullmatch(code):
        raise ApiError(400, "NOT_A_PRODUCT_CODE",
                       "This code is not a product barcode or a kitchen QR label",
                       [{"field": "code", "reason": f"'{code[:60]}' is not 8-14 digits"}])

    with get_conn() as conn:
        product, source = lookup(conn, code)
        data = ItemCreate(name=product["name"], brand=product["brand"],
                          category=product["category"], barcode=code)
        return ScanOut(code=code, source=source, item=add_item(conn, data))
