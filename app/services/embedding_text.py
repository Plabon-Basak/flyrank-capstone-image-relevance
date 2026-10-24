from typing import Any


def image_embedding_text(image: Any) -> str:
    attributes = image.attributes or {}
    attribute_text = " ".join(
        f"{key} {value}" for key, value in attributes.items()
    )

    return " ".join(
        str(part)
        for part in (
            image.subject,
            image.category,
            attribute_text,
            image.caption,
        )
        if part
    ).strip()


def blog_embedding_text(post: Any) -> str:
    return f"{post.title}\n{post.content}".strip()


def generate_embedding(provider: Any, text: str) -> list[float]:
    if not text:
        raise ValueError("Embedding text cannot be empty.")

    vectors = provider.embed([text])

    if len(vectors) != 1 or not vectors[0]:
        raise ValueError("Embedding provider returned an invalid vector.")

    return vectors[0]