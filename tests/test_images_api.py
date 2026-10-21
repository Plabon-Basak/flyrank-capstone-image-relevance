
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


def test_create_image(client, image_payload):
    response = client.post("/images", json=image_payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["filename"] == "fox.jpg"
    assert data["subject"] == "Red fox"
    assert data["status"] == "pending"


def test_list_images(client, image_payload):
    client.post("/images", json=image_payload)

    response = client.get("/images")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["filename"] == "fox.jpg"


def test_get_image(client, image_payload):
    created = client.post("/images", json=image_payload).json()

    response = client.get(f"/images/{created['id']}")

    assert response.status_code == 200
    assert response.json()["filename"] == "fox.jpg"


def test_get_missing_image(client):
    response = client.get("/images/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Image not found."


def test_duplicate_filename_returns_conflict(client, image_payload):
    client.post("/images", json=image_payload)

    response = client.post("/images", json=image_payload)

    assert response.status_code == 409


def test_invalid_confidence_is_rejected(client, image_payload):
    image_payload["confidence"] = 1.5

    response = client.post("/images", json=image_payload)

    assert response.status_code == 422
