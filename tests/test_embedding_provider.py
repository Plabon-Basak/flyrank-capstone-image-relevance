from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.embedding_provider import (
    EmbeddingProvider,
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
)


def test_embedding_provider_is_abstract():
    with pytest.raises(TypeError):
        EmbeddingProvider()


def test_mock_provider_reports_not_implemented():
    provider = MockEmbeddingProvider()

    with pytest.raises(
        NotImplementedError,
        match="Mock embeddings are not implemented yet",
    ):
        provider.embed(["A red fox in a forest"])


def test_openai_provider_requires_api_key():
    with pytest.raises(ValueError, match="EMBEDDING_API_KEY is required"):
        OpenAIEmbeddingProvider(api_key="")


def test_openai_provider_returns_embeddings_in_input_order():
    create_embeddings = Mock(
        return_value=SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.3, 0.4]),
                SimpleNamespace(index=0, embedding=[0.1, 0.2]),
            ]
        )
    )

    fake_client = SimpleNamespace(
        embeddings=SimpleNamespace(create=create_embeddings)
    )

    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model="test-embedding-model",
        client=fake_client,
    )

    result = provider.embed(["A fox", "A wolf"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    create_embeddings.assert_called_once_with(
        model="test-embedding-model",
        input=["A fox", "A wolf"],
    )


def test_openai_provider_returns_empty_list_without_api_call():
    create_embeddings = Mock()

    fake_client = SimpleNamespace(
        embeddings=SimpleNamespace(create=create_embeddings)
    )

    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        client=fake_client,
    )

    assert provider.embed([]) == []
    create_embeddings.assert_not_called()


def test_openai_provider_rejects_blank_text():
    create_embeddings = Mock()

    fake_client = SimpleNamespace(
        embeddings=SimpleNamespace(create=create_embeddings)
    )

    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        client=fake_client,
    )

    with pytest.raises(ValueError, match="non-empty strings"):
        provider.embed(["A fox", " "])

    create_embeddings.assert_not_called()