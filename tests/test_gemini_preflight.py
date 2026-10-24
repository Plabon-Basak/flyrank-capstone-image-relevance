from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import app, get_db
from app.services import api_usage_tracker, gemini_embedding_provider, metadata_provider
from app.services.api_usage_tracker import PricingNotConfiguredError


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_preflight_requires_all_gemini_pricing():
    with patch.object(api_usage_tracker.settings, "gemini_vision_input_cost_per_million_tokens", 0.0), \
         patch.object(api_usage_tracker.settings, "gemini_vision_output_cost_per_million_tokens", 3.75), \
         patch.object(api_usage_tracker.settings, "gemini_embedding_cost_per_million_characters", 0.00015), \
         patch.object(api_usage_tracker.settings, "api_budget_usd", 5.0):
        with pytest.raises(PricingNotConfiguredError):
            api_usage_tracker.APIUsageTracker.preflight(["vision", "embedding"])


def test_preflight_requires_budget():
    with patch.object(api_usage_tracker.settings, "gemini_vision_input_cost_per_million_tokens", 0.75), \
         patch.object(api_usage_tracker.settings, "gemini_vision_output_cost_per_million_tokens", 3.75), \
         patch.object(api_usage_tracker.settings, "gemini_embedding_cost_per_million_characters", 0.00015), \
         patch.object(api_usage_tracker.settings, "api_budget_usd", 0.0):
        with pytest.raises(PricingNotConfiguredError):
            api_usage_tracker.APIUsageTracker.preflight(["vision"])


@pytest.mark.anyio
async def test_gemini_metadata_provider_preflight_blocks_call():
    models = Mock()
    models.generate_content = Mock()
    client = Mock()
    client.models = models

    with patch.object(metadata_provider.genai, "Client", lambda **kwargs: client), \
         patch.object(api_usage_tracker.settings, "gemini_vision_input_cost_per_million_tokens", 0.75), \
         patch.object(api_usage_tracker.settings, "gemini_vision_output_cost_per_million_tokens", 3.75), \
         patch.object(api_usage_tracker.settings, "gemini_embedding_cost_per_million_characters", 0.00015), \
         patch.object(api_usage_tracker.settings, "api_budget_usd", 5.0), \
         patch.object(api_usage_tracker.settings, "gemini_api_key", "test-key"):
        from app.services.metadata_provider import GeminiMetadataProvider
        provider = GeminiMetadataProvider(client=client)

    with patch.object(api_usage_tracker.settings, "gemini_vision_input_cost_per_million_tokens", 0.0), \
         patch.object(api_usage_tracker.settings, "gemini_vision_output_cost_per_million_tokens", 3.75), \
         patch.object(api_usage_tracker.settings, "gemini_embedding_cost_per_million_characters", 0.00015), \
         patch.object(api_usage_tracker.settings, "api_budget_usd", 5.0):
        with pytest.raises(PricingNotConfiguredError):
            await provider.generate_metadata(__file__)
    models.generate_content.assert_not_called()


def test_gemini_embedding_provider_preflight_blocks_call():
    models = Mock()
    models.embed_content = Mock()
    client = Mock()
    client.models = models
    with patch.object(api_usage_tracker.settings, "gemini_embedding_cost_per_million_characters", 0.0), \
         patch.object(api_usage_tracker.settings, "api_budget_usd", 5.0), \
         patch.object(api_usage_tracker.settings, "gemini_api_key", "test-key"):
        provider = gemini_embedding_provider.GeminiEmbeddingProvider(client=client, dimensions=3)
        with pytest.raises(PricingNotConfiguredError):
            provider.embed(["hello"])
    models.embed_content.assert_not_called()


def test_analyze_image_preflight_blocks_before_vision(db_session):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch.object(api_usage_tracker.settings, "metadata_provider", "gemini"), \
             patch.object(api_usage_tracker.settings, "embedding_provider", "gemini"), \
             patch.object(api_usage_tracker.settings, "gemini_vision_input_cost_per_million_tokens", 0.0), \
             patch.object(api_usage_tracker.settings, "gemini_vision_output_cost_per_million_tokens", 3.75), \
             patch.object(api_usage_tracker.settings, "gemini_embedding_cost_per_million_characters", 0.00015), \
             patch.object(api_usage_tracker.settings, "api_budget_usd", 5.0), \
             patch.object(api_usage_tracker.settings, "gemini_api_key", "test-key"), \
             patch.object(api_usage_tracker.settings, "upload_dir", "./data/uploads"):
            client = TestClient(app)
            from app.models.image import Image
            from io import BytesIO
            from PIL import Image as PILImage
            import pathlib
            p = pathlib.Path("./data/uploads")
            p.mkdir(parents=True, exist_ok=True)
            buf = BytesIO()
            PILImage.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
            f = p / "preflight.jpg"
            f.write_bytes(buf.getvalue())
            with TestingSessionLocal() as db:
                img = Image(filename="preflight.jpg", file_path=f.as_posix(), status="pending")
                db.add(img)
                db.commit()
                db.refresh(img)
                img_id = img.id
            resp = client.post(f"/images/{img_id}/analyze")
            assert resp.status_code == 503
            assert "Gemini Vision pricing" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_blog_post_preflight_blocks_before_db_call(db_session):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch.object(api_usage_tracker.settings, "embedding_provider", "gemini"), \
             patch.object(api_usage_tracker.settings, "gemini_embedding_cost_per_million_characters", 0.0), \
             patch.object(api_usage_tracker.settings, "api_budget_usd", 5.0), \
             patch.object(api_usage_tracker.settings, "gemini_api_key", "test-key"):
            client = TestClient(app)
            resp = client.post(
                "/blog-posts",
                json={
                    "title": "Test",
                    "content": "Hello world",
                    "url": None,
                },
            )
            assert resp.status_code == 503
            assert "Gemini embedding pricing" in resp.json()["detail"]
        with db_session() as db:
            from app.models.blog_post import BlogPost
            assert db.query(BlogPost).count() == 0
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
