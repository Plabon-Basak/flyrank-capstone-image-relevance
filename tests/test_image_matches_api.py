
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.core.config import settings
from app.db.base import Base
from app.main import app, get_db


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

    with TestClient(app) as test_client:
        yield test_client

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
        response = client.get(f"/images/{created.json()['id']}/matches")

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
        response = client.get(f"/images/{created.json()['id']}/matches")

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
            "content": "Red foxes live in forests and other wildlife habitats.",
            "url": "https://example.com/foxes",
        },
    )
    assert created_post.status_code == 201

    fake_result = {
        "image_id": image_id,
        "status": "matched",
        "reason": "Eligible blog posts ranked by semantic similarity.",
        "matches": [
            {
                "blog_post_id": created_post.json()["id"],
                "title": "Foxes in forest habitats",
                "url": "https://example.com/foxes",
                "similarity": 0.91,
                "reason": "Semantic similarity calculated from image metadata and blog content.",
            }
        ],
    }

    with (
        patch.object(settings, "embedding_provider", "openai"),
        patch.object(settings, "embedding_api_key", "test-key"),
        patch(
            "app.main.OpenAIEmbeddingProvider"
        ) as mock_provider_class,
        patch(
            "app.main.MatchingService"
        ) as mock_service_class,
    ):
        mock_service_class.return_value.match.return_value = fake_result

        response = client.get(f"/images/{image_id}/matches")

    assert response.status_code == 200
    assert response.json() == fake_result
    mock_provider_class.assert_called_once()
    mock_service_class.return_value.match.assert_called_once()
