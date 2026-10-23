
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
        "attributes": {"animal": "fox"},
        "caption": "A red fox standing in a forest.",
        "confidence": 0.96,
    }


def create_image(client, image_payload):
    response = client.post("/images", json=image_payload)
    assert response.status_code == 201
    return response.json()


def test_create_batch_job(client, image_payload):
    image = create_image(client, image_payload)

    response = client.post(
        "/batch-jobs",
        json={"image_ids": [image["id"]]},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["image_ids"] == [image["id"]]
    assert data["status"] == "pending"
    assert data["total_items"] == 1
    assert data["processed_items"] == 0
    assert data["failed_items"] == 0
    assert data["retry_count"] == 0
    assert data["max_retries"] == 3
    assert data["estimated_cost_usd"] == 0.0
    assert data["started_at"] is None
    assert data["completed_at"] is None


def test_create_batch_job_with_custom_retries(client, image_payload):
    image = create_image(client, image_payload)

    response = client.post(
        "/batch-jobs",
        json={"image_ids": [image["id"]], "max_retries": 5},
    )

    assert response.status_code == 201
    assert response.json()["max_retries"] == 5


def test_get_batch_job(client, image_payload):
    image = create_image(client, image_payload)
    created = client.post(
        "/batch-jobs",
        json={"image_ids": [image["id"]]},
    ).json()

    response = client.get(f"/batch-jobs/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["image_ids"] == [image["id"]]
    assert response.json()["status"] == "pending"


def test_get_missing_batch_job(client):
    response = client.get("/batch-jobs/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Batch job not found."


def test_create_batch_job_rejects_missing_image_ids(client):
    response = client.post(
        "/batch-jobs",
        json={"image_ids": [999]},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["missing_image_ids"] == [999]


@pytest.mark.parametrize(
    "payload",
    [
        {"image_ids": []},
        {"image_ids": [1, 1]},
        {"image_ids": [0]},
        {"image_ids": [-1]},
        {"image_ids": [1], "max_retries": -1},
        {"image_ids": [1], "max_retries": 6},
        {"image_ids": [1], "unexpected": True},
    ],
)
def test_create_batch_job_rejects_invalid_payload(client, payload):
    response = client.post("/batch-jobs", json=payload)

    assert response.status_code == 422
