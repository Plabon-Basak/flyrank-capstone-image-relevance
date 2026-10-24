
import json

import pytest
from PIL import Image

from app.core.config import settings
from app.schemas.image import ImageMetadata
from app.services import metadata_provider
from app.services.metadata_provider import (
    GeminiMetadataProvider,
    MetadataProvider,
    MockMetadataProvider,
    get_metadata_provider,
)


@pytest.mark.anyio
async def test_mock_provider_returns_valid_metadata(tmp_path):
    provider = MockMetadataProvider()
    image_path = str(tmp_path / "example.jpg")

    result = await provider.generate_metadata(image_path)

    assert isinstance(result, ImageMetadata)
    assert result.subject == "Image not analyzed"
    assert result.category == "unclassified"
    assert result.confidence == 0.0
    assert result.attributes["provider"] == "mock"
    assert result.attributes["analysis_complete"] is False


@pytest.mark.anyio
async def test_mock_provider_obeys_metadata_schema(tmp_path):
    provider: MetadataProvider = MockMetadataProvider()

    result = await provider.generate_metadata(
        str(tmp_path / "example.jpg")
    )

    validated = ImageMetadata.model_validate(result.model_dump())

    assert 0.0 <= validated.confidence <= 1.0
    assert validated.caption
    assert validated.subject
    assert validated.category


def test_factory_returns_mock_provider(monkeypatch):
    monkeypatch.setattr(settings, "metadata_provider", "mock")

    provider = get_metadata_provider()

    assert isinstance(provider, MockMetadataProvider)


def test_factory_accepts_case_and_whitespace(monkeypatch):
    monkeypatch.setattr(settings, "metadata_provider", " MOCK ")

    provider = get_metadata_provider()

    assert isinstance(provider, MockMetadataProvider)


def test_factory_rejects_unsupported_provider(monkeypatch):
    monkeypatch.setattr(settings, "metadata_provider", "unknown")

    with pytest.raises(ValueError, match="Unsupported metadata provider"):
        get_metadata_provider()


def test_gemini_provider_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")

    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        GeminiMetadataProvider()


def test_factory_returns_gemini_provider(monkeypatch):
    monkeypatch.setattr(settings, "metadata_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-api-key")

    monkeypatch.setattr(
        metadata_provider.genai,
        "Client",
        lambda **kwargs: object(),
    )

    provider = get_metadata_provider()

    assert isinstance(provider, GeminiMetadataProvider)


@pytest.mark.anyio
async def test_gemini_provider_returns_valid_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "gemini_api_key", "test-api-key")
    monkeypatch.setattr(settings, "gemini_vision_model", "test-model")

    expected_response = {
        "subject": "A red car",
        "category": "vehicle",
        "attributes": {
            "color": "red",
            "object": "car",
        },
        "caption": "A red car parked beside a road.",
        "confidence": 0.95,
    }

    class FakeModels:
        def generate_content(self, **kwargs):
            assert kwargs["model"] == "test-model"
            assert kwargs["config"].response_mime_type == "application/json"
            return type(
                "FakeResponse",
                (),
                {"text": json.dumps(expected_response)},
            )()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(
        metadata_provider.genai,
        "Client",
        lambda **kwargs: FakeClient(),
    )

    image_path = tmp_path / "example.jpg"
    Image.new("RGB", (32, 32), color="red").save(image_path)

    provider = GeminiMetadataProvider()
    result = await provider.generate_metadata(str(image_path))

    assert isinstance(result, ImageMetadata)
    assert result.subject == "A red car"
    assert result.category == "vehicle"
    assert result.attributes["color"] == "red"
    assert result.attributes["provider"] == "gemini"
    assert result.attributes["analysis_complete"] is True
    assert result.confidence == 0.95
