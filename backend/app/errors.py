"""Every error leaves the API in one shape:
{"error": {"code": "NOT_FOUND", "message": "...", "details": [...], "requestId": "..."}}
"""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)

HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
}


class ApiError(Exception):
    """Raise this from any route to return a clean error response."""

    def __init__(self, status: int, code: str, message: str, details: list[dict] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def not_found(what: str) -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what} not found")


def invalid(field: str, reason: str) -> ApiError:
    return ApiError(400, "VALIDATION_FAILED", f"{field}: {reason}",
                    [{"field": field, "reason": reason}])


def _response(request: Request, status: int, code: str, message: str,
              details: list[dict] | None = None) -> JSONResponse:
    error = {"code": code, "message": message,
             "requestId": getattr(request.state, "request_id", None)}
    if details:
        error["details"] = details
    return JSONResponse({"error": error}, status_code=status)


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        # A short ID per request, returned in errors and as a header, to match
        # a user's error with the server log.
        request.state.request_id = uuid.uuid4().hex[:12]
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return _response(request, exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path")),
                    "reason": e["msg"]} for e in exc.errors()]
        return _response(request, 400, "VALIDATION_FAILED", "The request has invalid fields", details)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return _response(request, exc.status_code, HTTP_CODES.get(exc.status_code, "HTTP_ERROR"),
                         str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        log.exception("Unhandled error (request %s)", getattr(request.state, "request_id", "-"))
        return _response(request, 500, "INTERNAL_ERROR", "Something went wrong on the server")
