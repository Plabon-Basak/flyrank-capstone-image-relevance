
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.api_usage_tracker import PricingNotConfiguredError
from app.services.gemini_embedding_provider import GeminiEmbeddingProvider


class FakeModels:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def embed_content(self, **kwargs):
        self.calls.append(kwargs)

        if self.error:
            raise self.error

        return self.response


class FakeClient:
    def __init__(self, models):
        self.models = models


def test_gemini_embedding_returns_vectors():
    models = FakeModels(
        response=SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[0.1, 0.2, 0.3]),
                SimpleNamespace(values=[0.4, 0.5, 0.6]),
            ],
            metadata=SimpleNamespace(billable_character_count=20),
        )
    )

    provider = GeminiEmbeddingProvider(
        client=FakeClient(models),
        model="test-model",
        dimensions=3,
    )

    result = provider.embed(["first text", "second text"])

    assert result == [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]
    assert len(models.calls) == 1


def test_gemini_embedding_empty_input_does_not_call_api():
    models = FakeModels()

    provider = GeminiEmbeddingProvider(
        client=FakeClient(models),
        dimensions=3,
    )

    assert provider.embed([]) == []
    assert models.calls == []


def test_gemini_embedding_rejects_blank_input():
    provider = GeminiEmbeddingProvider(
        client=FakeClient(FakeModels()),
        dimensions=3,
    )

    with pytest.raises(ValueError):
        provider.embed(["   "])


def test_gemini_embedding_rejects_wrong_dimensions():
    models = FakeModels(
        response=SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[0.1, 0.2]),
            ],
        )
    )

    provider = GeminiEmbeddingProvider(
        client=FakeClient(models),
        dimensions=3,
    )

    with pytest.raises(ValueError):
        provider.embed(["test"])


def test_gemini_embedding_records_provider_usage(monkeypatch):
    monkeypatch.setattr(
        "app.services.gemini_embedding_provider.APIUsageTracker.calculate_embedding_cost",
        lambda characters: Decimal("0.005"),
    )

    tracker = Mock()
    tracker.reserve.return_value = 10

    models = FakeModels(
        response=SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[0.1, 0.2, 0.3]),
            ],
            metadata=SimpleNamespace(billable_character_count=10000),
        )
    )

    provider = GeminiEmbeddingProvider(
        client=FakeClient(models),
        model="test-model",
        dimensions=3,
        usage_tracker=tracker,
        image_id=25,
    )

    result = provider.embed(["test image"])

    assert result == [[0.1, 0.2, 0.3]]

    tracker.reserve.assert_called_once()
    tracker.complete.assert_called_once_with(
        10,
        billable_characters=10000,
        estimated_cost_usd=Decimal("0.005"),
        usage_source="provider",
    )
    tracker.fail.assert_not_called()


def test_gemini_embedding_rejects_unconfigured_pricing(monkeypatch):
    tracker = Mock()

    monkeypatch.setattr(
        "app.services.gemini_embedding_provider.APIUsageTracker.calculate_embedding_cost",
        lambda characters: (_ for _ in ()).throw(
            PricingNotConfiguredError("Pricing not configured")
        ),
    )

    models = FakeModels()

    provider = GeminiEmbeddingProvider(
        client=FakeClient(models),
        dimensions=3,
        usage_tracker=tracker,
    )

    with pytest.raises(PricingNotConfiguredError):
        provider.embed(["test image"])

    assert models.calls == []
    tracker.reserve.assert_not_called()


def test_gemini_embedding_records_failed_api_call(monkeypatch):
    monkeypatch.setattr(
        "app.services.gemini_embedding_provider.APIUsageTracker.calculate_embedding_cost",
        lambda characters: Decimal("0.005"),
    )

    tracker = Mock()
    tracker.reserve.return_value = 11

    models = FakeModels(
        error=RuntimeError("Gemini API unavailable")
    )

    provider = GeminiEmbeddingProvider(
        client=FakeClient(models),
        dimensions=3,
        usage_tracker=tracker,
    )

    with pytest.raises(RuntimeError, match="Gemini API unavailable"):
        provider.embed(["test image"])

    tracker.reserve.assert_called_once()
    tracker.fail.assert_called_once_with(
        11,
        "Gemini API unavailable",
    )
    tracker.complete.assert_not_called()
