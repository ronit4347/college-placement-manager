from app.core.config import Settings


def test_render_postgres_url_selects_installed_psycopg_driver():
    assert Settings(database_url="postgresql://dbuser:secret@host/database").database_url == (
        "postgresql+psycopg://dbuser:secret@host/database"
    )


def test_legacy_postgres_url_selects_installed_psycopg_driver():
    assert Settings(database_url="postgres://dbuser:secret@host/database").database_url == (
        "postgresql+psycopg://dbuser:secret@host/database"
    )


def test_explicit_sqlalchemy_driver_is_unchanged():
    configured = "postgresql+psycopg://dbuser:secret@host/database"
    assert Settings(database_url=configured).database_url == configured
