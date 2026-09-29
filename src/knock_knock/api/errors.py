from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from knock_knock.ports.repositories import OptimisticConcurrencyError
from knock_knock.services.demo import (
    DemoAuthorizationError,
    DemoNotFoundError,
    DemoValidationError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DemoAuthorizationError)
    async def authorization_error(
        _request: Request,
        exc: DemoAuthorizationError,
    ) -> JSONResponse:
        return _error(status.HTTP_403_FORBIDDEN, "forbidden", str(exc))

    @app.exception_handler(DemoNotFoundError)
    async def not_found_error(_request: Request, exc: DemoNotFoundError) -> JSONResponse:
        return _error(status.HTTP_404_NOT_FOUND, "not_found", str(exc))

    @app.exception_handler(DemoValidationError)
    async def validation_error(_request: Request, exc: DemoValidationError) -> JSONResponse:
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_request", str(exc))

    @app.exception_handler(OptimisticConcurrencyError)
    async def concurrency_error(
        _request: Request,
        exc: OptimisticConcurrencyError,
    ) -> JSONResponse:
        return _error(status.HTTP_409_CONFLICT, "stale_version", str(exc))

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(
        _request: Request,
        _exc: RequestValidationError,
    ) -> JSONResponse:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_request",
            "Request fields are missing or invalid",
        )

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return _error(exc.status_code, "http_error", message)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
