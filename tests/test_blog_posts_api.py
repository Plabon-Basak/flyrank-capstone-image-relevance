
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.db.base import Base
from app.main import app, get_db
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

    try:
        with patch(
            "app.main.get_embedding_provider",
            return_value=LexicalEmbeddingProvider(),
        ):
            with TestClient(app) as test_client:
                yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture
def blog_post_payload():
    return {
        "title": "Wildlife in the Forest",
        "content": (
            "Red foxes live in forests and grasslands. "
            "They hunt small mammals and birds."
        ),
        "url": "https://example.com/wildlife-forest",
    }


def test_create_blog_post(client, blog_post_payload):
    response = client.post("/blog-posts", json=blog_post_payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == blog_post_payload["title"]
    assert data["content"] == blog_post_payload["content"]
    assert data["url"] == blog_post_payload["url"]
    assert "created_at" in data


def test_list_blog_posts(client, blog_post_payload):
    client.post("/blog-posts", json=blog_post_payload)

    response = client.get("/blog-posts")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == blog_post_payload["title"]


def test_get_blog_post(client, blog_post_payload):
    created = client.post(
        "/blog-posts",
        json=blog_post_payload,
    ).json()

    response = client.get(f"/blog-posts/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["title"] == blog_post_payload["title"]


def test_get_missing_blog_post(client):
    response = client.get("/blog-posts/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Blog post not found."


@pytest.mark.parametrize(
    "payload",
    [
        {"content": "A blog post without a title"},
        {"title": "Missing content"},
        {"title": "", "content": "Content"},
        {
            "title": "Unexpected field",
            "content": "Content",
            "unexpected": True,
        },
    ],
)
def test_create_blog_post_rejects_invalid_payload(client, payload):
    response = client.post("/blog-posts", json=payload)

    assert response.status_code == 422
