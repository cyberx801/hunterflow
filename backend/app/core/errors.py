"""Error taxonomy and the consistent API error envelope (HF-NFR-004).

Every domain error maps to a stable machine-readable code plus an HTTP status.
Unhandled exceptions are logged with the correlation id and returned as a
generic envelope without internals leaking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import get_correlation_id, get_logger

log = get_logger("hunterflow.errors")


class ErrorCode(str, Enum):
    VALIDATION = "VALIDATION"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    CONFLICT = "CONFLICT"
    SCOPE_DENIED = "SCOPE_DENIED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    BAD_STATE = "BAD_STATE"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    PARSE_ERROR = "PARSE_ERROR"
    JOB_ERROR = "JOB_ERROR"
    CANCELLED = "CANCELLED"
    UPLOAD_REJECTED = "UPLOAD_REJECTED"
    INTERNAL = "INTERNAL"


@dataclass
class ApiError(Exception):
    code: ErrorCode
    message: str
    status: int = 400
    details: dict[str, Any] | None = None

    def to_payload(self) -> dict:
        payload: dict[str, Any] = {"code": self.code.value, "message": self.message}
        if self.details:
            payload["details"] = self.details
        cid = get_correlation_id()
        if cid:
            payload["correlation_id"] = cid
        return payload


def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"error": exc.to_payload()})


def _http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    mapping = {
        404: ErrorCode.NOT_FOUND,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        405: ErrorCode.VALIDATION,
    }
    code = mapping.get(exc.status_code, ErrorCode.INTERNAL)
    status = exc.status_code
    if status < 500:
        # Starlette raised it intentionally; keep its detail.
        detail = str(exc.detail) if exc.detail not in (None, "") else code.value
    else:
        detail = code.value
    err = ApiError(code=code, message=detail, status=status)
    return JSONResponse(status_code=status, content={"error": err.to_payload()})


def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    err = ApiError(
        code=ErrorCode.VALIDATION,
        message="Request validation failed",
        status=422,
        details={"errors": exc.errors()},
    )
    return JSONResponse(status_code=422, content={"error": err.to_payload()})


def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_exception", exc_info=exc)
    err = ApiError(code=ErrorCode.INTERNAL, message="Internal server error", status=500)
    return JSONResponse(status_code=500, content={"error": err.to_payload()})


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
