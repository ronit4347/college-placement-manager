from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str | None = None
    jwt_secret_key: str | None = None
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    frontend_url: str = "http://localhost:5173"
    ai_api_key: str | None = None
    ai_model: str = "gpt-4o-mini"
    ai_request_timeout_seconds: int = Field(default=25, ge=5, le=120)
    ai_max_resume_characters: int = Field(default=30000, ge=1000, le=100000)
    resume_upload_dir: Path = Path("backend/uploads/resumes")
    max_resume_size_bytes: int = Field(default=5 * 1024 * 1024, ge=1024, le=25 * 1024 * 1024)
    demo_seed_enabled: bool = False
    demo_admin_password: SecretStr | None = None
    demo_student_password: SecretStr | None = None
    demo_recruiter_password: SecretStr | None = None
    demo_interviewer_password: SecretStr | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver_for_render_postgres(cls, value: str | None) -> str | None:
        """Render supplies postgresql:// URLs; this app installs psycopg 3, not psycopg2."""
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return "postgresql+psycopg://" + value.removeprefix("postgres://")
            if value.startswith("postgresql://"):
                return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore"
    )


settings = Settings()
