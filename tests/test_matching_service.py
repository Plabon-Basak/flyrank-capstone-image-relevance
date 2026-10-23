
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.matching_service import MatchingService


class FakeEmbeddingProvider:
    def __init__(self, vectors):
        self.vectors = vectors
        self.received_texts = None

    def embed(self, texts):
        self.received_texts = texts
        return self.vectors


def make_image(
    subject="fox",
    category="wildlife",
    confidence=0.96,
    caption="A red fox standing in a forest",
    attributes=None,
):
    return SimpleNamespace(
        id=1,
        subject=subject,
        category=category,
        confidence=confidence,
        caption=caption,
        attributes=attributes or {"color": "red"},
    )


def make_post(
    post_id=1,
    title="Foxes in the forest",
    content="A fox is wildlife that lives in forest habitats.",
    url="https://example.com/foxes",
):
    return SimpleNamespace(
        id=post_id,
        title=title,
        content=content,
        url=url,
    )


def test_match_ranks_posts_by_similarity():
    provider = FakeEmbeddingProvider(
        [
            [1.0, 0.0],
            [0.8, 0.6],
            [0.6, 0.8],
        ]
    )
    service = MatchingService(provider, threshold=0.35)

    result = service.match(
        make_image(),
        [
            make_post(
                1,
                "Foxes in forests",
                "A fox is wildlife that lives in forest habitats.",
            ),
            make_post(
                2,
                "Wildlife photography",
                "Photographers capture wildlife, including foxes, in nature.",
            ),
        ],
    )

    assert result["status"] == "matched"
    assert [item["blog_post_id"] for item in result["matches"]] == [1, 2]
    assert result["matches"][0]["similarity"] == 0.8
    assert result["matches"][1]["similarity"] == 0.6


def test_match_returns_no_match_below_threshold():
    provider = FakeEmbeddingProvider(
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ]
    )
    service = MatchingService(provider, threshold=0.5)

    result = service.match(make_image(), [make_post()])

    assert result["status"] == "no_match"
    assert result["matches"][0]["similarity"] == 0.0


def test_match_rejects_explicit_wolf_fox_mismatch():
    provider = FakeEmbeddingProvider(
        [
            [1.0, 0.0],
            [1.0, 0.0],
        ]
    )
    service = MatchingService(provider)

    result = service.match(
        make_image(subject="fox"),
        [
            make_post(
                title="Wolves in the mountains",
                content="Wolves hunt in packs and live in mountain habitats.",
            )
        ],
    )

    assert result["status"] == "no_match"
    assert "mismatch guard" in result["reason"]
    assert provider.received_texts is None


def test_match_requires_review_for_low_confidence_image():
    provider = FakeEmbeddingProvider([])
    service = MatchingService(provider)

    result = service.match(
        make_image(confidence=0.2),
        [make_post()],
    )

    assert result["status"] == "review_required"
    assert result["matches"] == []
    assert provider.received_texts is None


def test_match_handles_no_blog_posts():
    provider = FakeEmbeddingProvider([])
    service = MatchingService(provider)

    result = service.match(make_image(), [])

    assert result["status"] == "no_match"
    assert result["matches"] == []
    assert provider.received_texts is None


def test_match_rejects_mismatched_embedding_count():
    provider = FakeEmbeddingProvider([[1.0, 0.0]])
    service = MatchingService(provider)

    with pytest.raises(
        ValueError,
        match="unexpected number of vectors",
    ):
        service.match(make_image(), [make_post()])


def test_match_rejects_embedding_dimension_mismatch():
    provider = FakeEmbeddingProvider(
        [
            [1.0, 0.0],
            [1.0, 0.0, 0.0],
        ]
    )
    service = MatchingService(provider)

    with pytest.raises(
        ValueError,
        match="equal dimensions",
    ):
        service.match(make_image(), [make_post()])


def test_match_rejects_invalid_threshold():
    provider = FakeEmbeddingProvider([])

    with pytest.raises(ValueError, match="Threshold"):
        MatchingService(provider, threshold=1.5)
