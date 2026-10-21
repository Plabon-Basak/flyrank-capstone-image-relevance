import pytest
from pydantic import ValidationError

from app.schemas.image import ImageMetadata


def test_valid_image_metadata():
    metadata = ImageMetadata(
        subject="Red fox",
        category="wildlife",
        attributes={"color": "red", "environment": "forest"},
        caption="A red fox standing in a forest.",
        confidence=0.95,
    )

    assert metadata.subject == "Red fox"
    assert metadata.confidence == 0.95


def test_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValidationError):
        ImageMetadata(
            subject="Red fox",
            category="wildlife",
            caption="A fox in a forest.",
            confidence=1.5,
        )


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        ImageMetadata(
            subject="Red fox",
            category="wildlife",
            caption="A fox in a forest.",
            confidence=0.95,
            unexpected_field="not allowed",
        )
