
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.main import app, get_db
from app.services import api_usage_tracker
from app.services.embedding_factory import (
    get_embedding_provider as original_get_embedding_provider,
)
from app.services.embedding_provider import LexicalEmbeddingProvider


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    def test_embedding_provider(*args, **kwargs):
        if settings.embedding_provider.strip().lower() == "gemini":
            return LexicalEmbeddingProvider()

        return original_get_embedding_provider(*args, **kwargs)

    try:
        with patch.object(api_usage_tracker.settings, "gemini_vision_input_cost_per_million_tokens", 0.75), \
             patch.object(api_usage_tracker.settings, "gemini_vision_output_cost_per_million_tokens", 3.75), \
             patch.object(api_usage_tracker.settings, "gemini_embedding_cost_per_million_characters", 0.00015), \
             patch.object(api_usage_tracker.settings, "api_budget_usd", 5.0):
            with patch(
                "app.main.get_embedding_provider",
                side_effect=test_embedding_provider,
            ):
                with TestClient(app) as test_client:
                    yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture
def image_payload():
    return {
        "filename": "fox.jpg",
        "file_path": "data/images/fox.jpg",
        "subject": "Red fox",
        "category": "wildlife",
        "attributes": {"color": "red", "animal": "fox"},
        "caption": "A red fox standing in a forest.",
        "confidence": 0.96,
    }


def test_matches_returns_404_for_missing_image(client):
    response = client.get("/images/999/matches")

    assert response.status_code == 404
    assert response.json()["detail"] == "Image not found."


def test_matches_returns_503_when_provider_is_not_openai(
    client,
    image_payload,
):
    created = client.post("/images", json=image_payload)
    assert created.status_code == 201

    with patch.object(settings, "embedding_provider", "mock"):
        response = client.get(
            f"/images/{created.json()['id']}/matches"
        )

    assert response.status_code == 503
    assert "Semantic matching is not configured" in response.json()["detail"]


def test_matches_returns_503_when_api_key_is_missing(
    client,
    image_payload,
):
    created = client.post("/images", json=image_payload)
    assert created.status_code == 201

    with (
        patch.object(settings, "embedding_provider", "openai"),
        patch.object(settings, "embedding_api_key", ""),
    ):
        response = client.get(
            f"/images/{created.json()['id']}/matches"
        )

    assert response.status_code == 503
    assert "EMBEDDING_API_KEY" in response.json()["detail"]


def test_matches_returns_ranked_results_without_openai_api_call(
    client,
    image_payload,
):
    created_image = client.post("/images", json=image_payload)
    assert created_image.status_code == 201

    image_id = created_image.json()["id"]

    created_post = client.post(
        "/blog-posts",
        json={
            "title": "Foxes in forest habitats",
            "content": (
                "Red foxes live in forests and other wildlife habitats."
            ),
            "url": "https://example.com/foxes",
        },
    )
    assert created_post.status_code == 201

    blog_post_id = created_post.json()["id"]

    fake_result = {
        "image_id": image_id,
        "status": "matched",
        "reason": "Eligible blog posts ranked by semantic similarity.",
        "matches": [
            {
                "blog_post_id": blog_post_id,
                "title": "Foxes in forest habitats",
                "url": "https://example.com/foxes",
                "similarity": 0.91,
                "reason": (
                    "Semantic similarity calculated from image metadata "
                    "and blog content."
                ),
            }
        ],
    }

    with (
        patch.object(settings, "embedding_provider", "openai"),
        patch.object(settings, "embedding_api_key", "test-key"),
        patch("app.main.OpenAIEmbeddingProvider") as mock_provider_class,
        patch("app.main.MatchingService") as mock_service_class,
    ):
        mock_service_class.return_value.match.return_value = fake_result

        response = client.get(f"/images/{image_id}/matches")

    assert response.status_code == 200

    data = response.json()

    assert data["image_id"] == image_id
    assert data["status"] == "matched"
    assert len(data["matches"]) == 1

    match = data["matches"][0]

    assert match["blog_post_id"] == blog_post_id
    assert match["title"] == "Foxes in forest habitats"
    assert match["similarity"] == 0.91
    assert match["review_status"] == "pending"
    assert isinstance(match["suggestion_id"], int)

    mock_provider_class.assert_called_once()
    mock_service_class.return_value.match.assert_called_once()


def test_below_threshold_no_match_does_not_persist_suggestions(
    client,
    image_payload,
):
    created_image = client.post("/images", json=image_payload)
    assert created_image.status_code == 201
    image_id = created_image.json()["id"]

    created_post = client.post(
        "/blog-posts",
        json={
            "title": "Foxes in forest habitats",
            "content": (
                "Red foxes live in forests and other wildlife habitats."
            ),
            "url": "https://example.com/foxes",
        },
    )
    assert created_post.status_code == 201

    fake_result = {
        "image_id": image_id,
        "status": "no_match",
        "reason": "No eligible blog post reached the similarity threshold.",
        "matches": [
            {
                "blog_post_id": created_post.json()["id"],
                "title": "Foxes in forest habitats",
                "url": "https://example.com/foxes",
                "similarity": 0.10,
                "reason": "Semantic similarity calculated from image metadata and blog content.",
            }
        ],
    }

    with (
        patch.object(settings, "embedding_provider", "openai"),
        patch.object(settings, "embedding_api_key", "test-key"),
        patch("app.main.OpenAIEmbeddingProvider"),
        patch("app.main.MatchingService") as mock_service_class,
        patch("app.main.save_match_suggestions") as mock_save,
    ):
        mock_service_class.return_value.match.return_value = fake_result

        response = client.get(f"/images/{image_id}/matches")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_match"
    assert data["matches"] == []
    mock_save.assert_not_called()


def test_review_required_does_not_persist_suggestions(
    client,
    image_payload,
):
    created_image = client.post("/images", json=image_payload)
    assert created_image.status_code == 201
    image_id = created_image.json()["id"]

    created_post = client.post(
        "/blog-posts",
        json={
            "title": "Foxes in forest habitats",
            "content": (
                "Red foxes live in forests and other wildlife habitats."
            ),
            "url": "https://example.com/foxes",
        },
    )
    assert created_post.status_code == 201

    fake_result = {
        "image_id": image_id,
        "status": "review_required",
        "reason": "Image confidence is too low for reliable matching.",
        "matches": [],
    }

    with (
        patch.object(settings, "embedding_provider", "openai"),
        patch.object(settings, "embedding_api_key", "test-key"),
        patch("app.main.OpenAIEmbeddingProvider"),
        patch("app.main.MatchingService") as mock_service_class,
        patch("app.main.save_match_suggestions") as mock_save,
    ):
        mock_service_class.return_value.match.return_value = fake_result

        response = client.get(f"/images/{image_id}/matches")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "review_required"
    assert data["matches"] == []
    mock_save.assert_not_called()
