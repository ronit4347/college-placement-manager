import json
import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def sanitized_validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    """Return useful validation locations/messages without reflecting submitted values."""
    details = [
        {"loc": issue.get("loc", ()), "msg": issue.get("msg", "Invalid value."), "type": issue.get("type", "value_error")}
        for issue in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


def install_security_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, sanitized_validation_error_handler)


class UploadRequestTooLarge(Exception):
    pass


class UploadBodyLimitMiddleware:
    """Bound multipart request bytes before Starlette spools uploaded files."""

    def __init__(self, app, max_file_size_bytes: int, multipart_overhead_bytes: int = 64 * 1024):
        self.app = app
        self.max_request_bytes = max_file_size_bytes + multipart_overhead_bytes

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        is_resume_upload = path == "/api/students/me/resume" or bool(
            re.fullmatch(r"/api/students/-?[0-9]+/resume", path)
        )
        if scope.get("type") != "http" or scope.get("method") != "POST" or not is_resume_upload:
            await self.app(scope, receive, send)
            return

        async def reject_request():
            body = json.dumps({"detail": "Resume upload request is too large."}).encode()
            await send({"type": "http.response.start", "status": 413,
                        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
            await send({"type": "http.response.body", "body": body})

        content_length = next((value for name, value in scope.get("headers", []) if name.lower() == b"content-length"), None)
        if content_length is not None:
            try:
                if int(content_length) > self.max_request_bytes:
                    await reject_request()
                    return
            except ValueError:
                await reject_request()
                return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_request_bytes:
                    raise UploadRequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except UploadRequestTooLarge:
            await reject_request()
