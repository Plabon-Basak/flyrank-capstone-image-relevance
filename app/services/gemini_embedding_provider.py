
from google import genai
from google.genai import types

from app.core.config import settings
from app.services.api_usage_tracker import APIUsageTracker


class GeminiEmbeddingProvider:
    supports_persistent_embeddings = True

    def __init__(
        self,
        client=None,
        model=None,
        dimensions=None,
        usage_tracker=None,
        image_id=None,
        blog_post_id=None,
    ):
        self.model = model or settings.gemini_embedding_model
        self.dimensions = dimensions or settings.gemini_embedding_dimensions
        self.usage_tracker = usage_tracker
        self.image_id = image_id
        self.blog_post_id = blog_post_id

        if client is None:
            if not settings.gemini_api_key.strip():
                raise ValueError(
                    "GEMINI_API_KEY is required for Gemini embeddings."
                )

            client = genai.Client(api_key=settings.gemini_api_key)

        self.client = client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if any(
            not isinstance(text, str) or not text.strip()
            for text in texts
        ):
            raise ValueError("Embedding inputs must be non-empty strings.")

        usage_id = None

        if self.usage_tracker is not None:
            estimated_characters = sum(len(text) for text in texts)

            estimated_cost = APIUsageTracker.calculate_embedding_cost(
                estimated_characters
            )

            usage_id = self.usage_tracker.reserve(
                model=self.model,
                operation="embedding",
                estimated_cost_usd=estimated_cost,
                image_id=self.image_id,
                blog_post_id=self.blog_post_id,
            )

        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="SEMANTIC_SIMILARITY",
                    output_dimensionality=self.dimensions,
                ),
            )
        except Exception as exc:
            if usage_id is not None:
                try:
                    self.usage_tracker.fail(usage_id, str(exc))
                except Exception:
                    pass
            raise

        try:
            embeddings = [
                list(item.values)
                for item in response.embeddings
            ]

            if len(embeddings) != len(texts):
                raise ValueError(
                    "Gemini returned an unexpected number of embeddings."
                )

            if any(
                len(vector) != self.dimensions
                for vector in embeddings
            ):
                raise ValueError(
                    "Gemini returned an unexpected embedding dimension."
                )

        except Exception as exc:
            if usage_id is not None:
                try:
                    self.usage_tracker.fail(usage_id, str(exc))
                except Exception:
                    pass
            raise

        if usage_id is not None:
            metadata = getattr(response, "metadata", None)

            billable_characters = getattr(
                metadata,
                "billable_character_count",
                None,
            )

            if billable_characters is not None:
                actual_cost = APIUsageTracker.calculate_embedding_cost(
                    billable_characters
                )

                self.usage_tracker.complete(
                    usage_id,
                    billable_characters=billable_characters,
                    estimated_cost_usd=actual_cost,
                    usage_source="provider",
                )
            else:
                self.usage_tracker.complete(
                    usage_id,
                    usage_source="estimated",
                )

        return embeddings
