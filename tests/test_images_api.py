
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.main import app, get_db
from app.schemas.image import ImageMetadata
from app.services.embedding_provider import LexicalEmbeddingProvider


class FakeMetadataProvider:
    def __init__(self, confidence=0.95):
        self.confidence = confidence

    async def generate_metadata(self, image_path):
        return ImageMetadata(
            subject="Red fox",
            category="wildlife",
            attributes={"animal": "fox", "color": "red"},
            caption="A red fox standing outdoors.",
            confidence=self.confidence,
        )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

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


def create_test_image():
    image = PILImage.new("RGB", (100, 100), color="red")
    image_bytes = BytesIO()
    image.save(image_bytes, format="JPEG")
    image_bytes.seek(0)
    return image_bytes


def create_image(client, tmp_path, filename="fox.jpg"):
    image_path = tmp_path / filename
    image_path.write_bytes(create_test_image().getvalue())

    response = client.post(
        "/images",
        json={
            "filename": filename,
            "file_path": str(image_path),
            "subject": "Red fox",
            "category": "wildlife",
            "attributes": {"animal": "fox"},
            "caption": "A red fox standing outdoors.",
            "confidence": 0.95,
        },
    )

    return response


def test_create_image(client, tmp_path):
    response = create_image(client, tmp_path)

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "fox.jpg"
    assert data["category"] == "wildlife"
    assert data["subject"] == "Red fox"
    assert data["status"] == "pending"


def test_create_image_rejects_missing_required_fields(client):
    response = client.post(
        "/images",
        json={
            "filename": "fox.jpg",
            "file_path": "data/uploads/fox.jpg",
        },
    )

    assert response.status_code == 422


def test_upload_image(client):
    response = client.post(
        "/images/upload",
        files={
            "file": (
                "fox.jpg",
                create_test_image(),
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"].endswith(".jpg")
    assert data["filename"] != ""
    assert data["file_path"]
    assert data["status"] == "pending"
    assert Path(data["file_path"]).is_file()


def test_upload_image_rejects_invalid_file(client):
    response = client.post(
        "/images/upload",
        files={
            "file": (
                "invalid.jpg",
                b"This is not a valid image.",
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 400


def test_list_images(client, tmp_path):
    create_image(client, tmp_path)

    response = client.get("/images")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["filename"] == "fox.jpg"


def test_get_image(client, tmp_path):
    create_response = create_image(client, tmp_path)
    image_id = create_response.json()["id"]

    response = client.get(f"/images/{image_id}")

    assert response.status_code == 200
    assert response.json()["id"] == image_id
    assert response.json()["filename"] == "fox.jpg"


def test_get_image_returns_404_for_missing_image(client):
    response = client.get("/images/9999")

    assert response.status_code == 404


def test_analyze_image(client, tmp_path, monkeypatch):
    image_response = create_image(client, tmp_path)
    image_id = image_response.json()["id"]

    monkeypatch.setattr(
        "app.main.get_metadata_provider",
        lambda **kwargs: FakeMetadataProvider(),
    )

    response = client.post(f"/images/{image_id}/analyze")

    assert response.status_code == 200
    data = response.json()
    assert data["image_id"] == image_id
    assert data["status"] == "analysis_completed"
    assert data["review_required"] is False
    assert data["metadata"]["subject"] == "Red fox"
    assert data["metadata"]["category"] == "wildlife"


def test_analyze_image_returns_404_for_missing_image(client):
    response = client.post("/images/9999/analyze")

    assert response.status_code == 404


def test_analyze_image_returns_404_when_file_is_missing(client, tmp_path):
    image_path = tmp_path / "missing.jpg"

    response = client.post(
        "/images",
        json={
            "filename": "missing.jpg",
            "file_path": str(image_path),
            "subject": "Unknown",
            "category": "unknown",
            "attributes": {},
            "caption": "Missing image.",
            "confidence": 0.5,
        },
    )

    image_id = response.json()["id"]

    analyze_response = client.post(f"/images/{image_id}/analyze")

    assert analyze_response.status_code == 404


def test_analyze_image_requires_review_for_low_confidence(
    client,
    tmp_path,
    monkeypatch,
):
    image_response = create_image(client, tmp_path)
    image_id = image_response.json()["id"]

    monkeypatch.setattr(
        "app.main.get_metadata_provider",
        lambda **kwargs: FakeMetadataProvider(confidence=0.45),
    )

    response = client.post(f"/images/{image_id}/analyze")

    assert response.status_code == 200
    assert response.json()["review_required"] is True
    assert response.json()["metadata"]["confidence"] == 0.45


def test_analyze_image_does_not_require_review_for_high_confidence(
    client,
    tmp_path,
    monkeypatch,
):
    image_response = create_image(client, tmp_path)
    image_id = image_response.json()["id"]

    monkeypatch.setattr(
        "app.main.get_metadata_provider",
        lambda **kwargs: FakeMetadataProvider(confidence=0.95),
    )

    response = client.post(f"/images/{image_id}/analyze")

    assert response.status_code == 200
    assert response.json()["review_required"] is False
    assert response.json()["metadata"]["confidence"] == 0.95


def test_analyze_image_returns_502_when_metadata_provider_fails(
    client,
    tmp_path,
    monkeypatch,
):
    image_response = create_image(client, tmp_path)
    image_id = image_response.json()["id"]

    class FailingMetadataProvider:
        async def generate_metadata(self, image_path):
            raise RuntimeError("Metadata provider failed")

    monkeypatch.setattr(
        "app.main.get_metadata_provider",
        lambda **kwargs: FailingMetadataProvider(),
    )

    response = client.post(f"/images/{image_id}/analyze")

    assert response.status_code == 502
