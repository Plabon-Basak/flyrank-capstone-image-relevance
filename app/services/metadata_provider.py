from typing import Protocol

from app.schemas.image import ImageMetadata

from app.core.config import settings


class MetadataProvider(Protocol):
    async def generate_metadata(self, image_path: str) -> ImageMetadata:
        ...


class MockMetadataProvider:
    async def generate_metadata(self, image_path: str) -> ImageMetadata:
        return ImageMetadata(
            subject="Image not analyzed",
            category="unclassified",
            attributes={
                "provider": "mock",
                "analysis_complete": False,
            },
            caption=(
                "Placeholder metadata from the mock provider. "
                "The image has not been analyzed by a vision model."
            ),
            confidence=0.0,
        )




def get_metadata_provider() -> MetadataProvider:
    provider_name = settings.metadata_provider.strip().lower()

    if provider_name == "mock":
        return MockMetadataProvider()

    raise ValueError(
        f"Unsupported metadata provider: {provider_name}"
    )
