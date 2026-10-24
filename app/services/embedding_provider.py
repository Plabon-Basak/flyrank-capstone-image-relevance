import math
import re
from abc import ABC, abstractmethod
from collections import Counter

from openai import OpenAI

from app.core.config import settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Mock embeddings are not implemented yet."
        )


class LexicalEmbeddingProvider(EmbeddingProvider):
    """Local TF-IDF-style lexical vectors; not a neural embedding model."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Embedding inputs must be non-empty strings.")

        def normalize_token(token: str) -> str:
            if len(token) > 4 and token.endswith("ies"):
               return token[:-3] + "y"
            if len(token) > 4 and token.endswith(("ches", "shes", "xes", "zes", "ses")):
               return token[:-2]
            if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
               return token[:-1]
            return token


        tokenized = [
            [
                normalize_token(token)
                for token in re.findall(r"[a-z0-9]+", text.lower())
            ]
            for text in texts
        ]
        document_count = len(tokenized)
        vocab = sorted({token for tokens in tokenized for token in tokens})

        document_frequency = {
            token: sum(token in set(tokens) for tokens in tokenized)
            for token in vocab
        }

        vectors = []
        for tokens in tokenized:
            counts = Counter(tokens)
            vector = []
            for token in vocab:
                term_frequency = counts[token] / max(len(tokens), 1)
                inverse_document_frequency = math.log(
                    (1 + document_count)
                    / (1 + document_frequency[token])
                ) + 1
                vector.append(term_frequency * inverse_document_frequency)

            norm = math.sqrt(sum(value * value for value in vector))
            if norm:
                vector = [value / norm for value in vector]
            vectors.append(vector)

        return vectors


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client=None,
    ):
        self.model = model or settings.embedding_model

        if client is None:
            key = settings.embedding_api_key if api_key is None else api_key

            if not key or not key.strip():
                raise ValueError(
                    "EMBEDDING_API_KEY is required to use OpenAI embeddings."
                )

            client = OpenAI(api_key=key)

        self.client = client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Embedding inputs must be non-empty strings.")

        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )

        ordered_data = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered_data]
