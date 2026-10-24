
from app.core.config import settings
from app.services.api_usage_tracker import APIUsageTracker
from app.services.embedding_provider import (
    LexicalEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from app.services.gemini_embedding_provider import GeminiEmbeddingProvider


def get_embedding_provider(
    usage_tracker: APIUsageTracker | None = None,
    image_id: int | None = None,
    blog_post_id: int | None = None,
):
    provider_name = settings.embedding_provider.strip().lower()

    if provider_name == "gemini":
        return GeminiEmbeddingProvider(
            usage_tracker=usage_tracker,
            image_id=image_id,
            blog_post_id=blog_post_id,
        )

    if provider_name == "openai":
        return OpenAIEmbeddingProvider()

    if provider_name == "lexical":
        return LexicalEmbeddingProvider()

    raise ValueError(
        "Unsupported embedding provider. Use gemini, openai, or lexical."
    )
