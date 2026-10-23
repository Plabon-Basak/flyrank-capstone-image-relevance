import pytest
from app.core.config import settings
from app.services.metadata_provider import get_metadata_provider

from app.schemas.image import ImageMetadata
from app.services.metadata_provider import (
    MetadataProvider,
    MockMetadataProvider,
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