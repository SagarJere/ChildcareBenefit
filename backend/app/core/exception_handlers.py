"""Centralized exception handling.

Ensures every error response follows a consistent, safe envelope and that no
stack trace or internal database error ever reaches a client.
"""
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.request_context import get_correlation_id

logger = logging.getLogger(__name__)


def _error_body(code: str, message: str, details=None) -> dict:
    return {
        "code": code,
        "message": message,
        "details": details,
        "correlationId": get_correlation_id(),
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code=f"HTTP_{exc.status_code}", message=str(exc.detail)),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body(
                code="VALIDATION_ERROR",
                message="Request validation failed.",
                # Pydantic error dicts can carry a "ctx" entry containing
                # the raw exception object (e.g. from a custom validator's
                # `raise ValueError(...)`), which json.dumps cannot
                # serialize on its own — jsonable_encoder converts it to a
                # plain string first, the same way FastAPI's own default
                # validation-error handler does.
                details=jsonable_encoder(exc.errors()),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception while processing %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred. Please try again later.",
            ),
        )
