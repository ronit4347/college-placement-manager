from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

from app.core.errors import UploadBodyLimitMiddleware
from app.main import app
from pathlib import Path
import pytest


def test_cors_is_single_origin_and_does_not_allow_credentialed_cookies():
    cors = next(item for item in app.user_middleware if item.cls is CORSMiddleware)
    assert cors.kwargs["allow_credentials"] is False
    assert cors.kwargs["allow_origins"]
    assert "*" not in cors.kwargs["allow_origins"]
    assert "*" not in cors.kwargs["allow_headers"]


@pytest.mark.parametrize("path", ["/api/students/me/resume", "/api/students/01/resume"])
def test_resume_multipart_body_limit_rejects_oversized_request_before_route(path):
    limited_app = FastAPI()
    limited_app.add_middleware(UploadBodyLimitMiddleware, max_file_size_bytes=1024)

    @limited_app.post("/api/students/me/resume")
    async def upload():
        return {"accepted": True}

    response = TestClient(limited_app).post(
        path,
        files={"file": ("resume.pdf", b"x" * (70 * 1024), "application/pdf")},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "Resume upload request is too large."


def test_upload_limit_does_not_affect_other_requests():
    limited_app = FastAPI()
    limited_app.add_middleware(UploadBodyLimitMiddleware, max_file_size_bytes=1024)

    @limited_app.post("/api/other")
    async def other():
        return {"accepted": True}

    response = TestClient(limited_app).post("/api/other", content=b"x" * (70 * 1024))
    assert response.status_code == 200
    assert response.json() == {"accepted": True}


def test_environment_example_does_not_contain_an_accepted_jwt_secret():
    example = Path(__file__).resolve().parents[2] / ".env.example"
    entries = dict(line.split("=", 1) for line in example.read_text().splitlines() if line and not line.lstrip().startswith("#") and "=" in line)
    assert not entries.get("JWT_SECRET_KEY", "").strip()
