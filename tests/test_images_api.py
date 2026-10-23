
from io import BytesIO
from app.schemas.image import ImageMetadata
import pytest
from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


def make_test_image(image_format="PNG"):
    buffer = BytesIO()
    PILImage.new("RGB", (10, 10), color="blue").save(
        buffer,
        format=image_format,
    )
    return buffer.getvalue()


def test_upload_valid_image(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    response = client.post(
        "/images/upload",
        files={
            "file": (
                "test.png",
                make_test_image(),
                "image/png",
            )
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"].endswith(".png")
    assert data["status"] == "pending"
    assert (tmp_path / data["filename"]).is_file()


def test_upload_rejects_invalid_image(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    response = client.post(
        "/images/upload",
        files={
            "file": (
                "fake.png",
                b"not an image",
                "image/png",
            )
        },
    )

    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_unsupported_image(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    response = client.post(
        "/images/upload",
        files={
            "file": (
                "test.bmp",
                make_test_image("BMP"),
                "image/bmp",
            )
        },
    )

    assert response.status_code == 415
    assert list(tmp_path.iterdir()) == []


def test_analyze_image_with_mock_provider(
    client,
    image_payload,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "metadata_provider", "mock")

    image_file = tmp_path / "fox.jpg"
    image_file.write_bytes(make_test_image("JPEG"))
    image_payload["file_path"] = str(image_file)

    created = client.post("/images", json=image_payload).json()

    response = client.post(f"/images/{created['id']}/analyze")

    assert response.status_code == 200
    data = response.json()
    assert data["image_id"] == created["id"]
    assert data["status"] == "mock_analysis"
    assert "No real image analysis was performed." in data["message"]
    assert data["metadata"]["attributes"]["provider"] == "mock"
    assert data["metadata"]["confidence"] == 0.0

    stored = client.get(f"/images/{created['id']}").json()
    assert stored["status"] == "pending"
    assert stored["subject"] == image_payload["subject"]
    assert stored["confidence"] == image_payload["confidence"]
    assert stored["review_required"] is False


def test_analyze_missing_image(client):
    response = client.post("/images/999/analyze")

    assert response.status_code == 404
    assert response.json()["detail"] == "Image not found."




def test_analyze_image_rejects_unsupported_provider(
    client,
    image_payload,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "metadata_provider", "unknown")

    image_file = tmp_path / "fox.jpg"
    image_file.write_bytes(make_test_image("JPEG"))
    image_payload["file_path"] = str(image_file)

    created = client.post("/images", json=image_payload).json()

    response = client.post(
        f"/images/{created['id']}/analyze"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The configured metadata provider is unavailable."
    )

class FakeMetadataProvider:
    def __init__(self, confidence):
        self.confidence = confidence

    async def generate_metadata(self, image_path):
        return ImageMetadata(
            subject="Red fox",
            category="wildlife",
            attributes={
                "animal": "fox",
                "provider": "fake-test-provider",
            },
            caption="A red fox standing in a forest.",
            confidence=self.confidence,
        )


@pytest.mark.parametrize(
    ("confidence", "expected_review"),
    [
        (0.45, True),
        (0.69, True),
        (0.70, False),
        (0.96, False),
    ],
)
def test_analyze_persists_metadata_and_review_flag(
    client,
    image_payload,
    monkeypatch,
    tmp_path,
    confidence,
    expected_review,
):
    image_file = tmp_path / "fox.jpg"
    image_file.write_bytes(make_test_image("JPEG"))
    image_payload["file_path"] = str(image_file)

    created = client.post("/images", json=image_payload).json()

    monkeypatch.setattr(
        "app.main.get_metadata_provider",
        lambda: FakeMetadataProvider(confidence),
    )

    response = client.post(
        f"/images/{created['id']}/analyze"
    )

    assert response.status_code == 200

    result = response.json()
    assert result["status"] == "analysis_completed"
    assert result["review_required"] is expected_review
    assert result["metadata"]["confidence"] == confidence

    stored_response = client.get(
        f"/images/{created['id']}"
    )
    assert stored_response.status_code == 200

    stored = stored_response.json()
    assert stored["subject"] == "Red fox"
    assert stored["category"] == "wildlife"
    assert stored["caption"] == "A red fox standing in a forest."
    assert stored["confidence"] == confidence
    assert stored["review_required"] is expected_review
    assert stored["status"] == "completed"
