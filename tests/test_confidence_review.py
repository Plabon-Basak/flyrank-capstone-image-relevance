
import pytest

from app.services.confidence_review import requires_review


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (0.0, True),
        (0.45, True),
        (0.69, True),
        (0.70, False),
        (0.96, False),
        (1.0, False),
    ],
)
def test_requires_review(confidence, expected):
    assert requires_review(confidence) is expected


def test_custom_threshold():
    assert requires_review(0.75, threshold=0.80) is True
    assert requires_review(0.85, threshold=0.80) is False
