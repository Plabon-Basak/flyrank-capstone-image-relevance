from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.db.base import Base
from app.db.session import SessionLocal, engine


def test_default_settings():
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.database_url == "sqlite:///./image_matching_test.db"


def test_image_table_is_registered():
    assert "images" in Base.metadata.tables


def test_database_engine_configuration():
    assert engine.dialect.name == "sqlite"
    assert make_url(engine.url).database == "./image_matching_test.db"
    assert SessionLocal.kw["bind"] is engine
