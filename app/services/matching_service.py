import math
import re
from typing import Any

from app.services.embedding_provider import EmbeddingProvider


class MatchingService:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        threshold: float = 0.35,
        minimum_image_confidence: float = 0.5,
    ):
        if not 0 <= threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1.")

        if not 0 <= minimum_image_confidence <= 1:
            raise ValueError(
                "Minimum image confidence must be between 0 and 1."
            )

        self.embedding_provider = embedding_provider
        self.threshold = threshold
        self.minimum_image_confidence = minimum_image_confidence

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    @classmethod
    def _image_text(cls, image: Any) -> str:
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

    @staticmethod
    def _blog_text(post: Any) -> str:
        return f"{post.title}\n{post.content}".strip()

    @classmethod
    def _has_explicit_mismatch(cls, image: Any, post: Any) -> bool:
        subject = cls._normalize(image.subject or "")
        category = cls._normalize(image.category or "")
        blog_text = cls._normalize(
            f"{post.title} {post.content}"
        )

        if not subject or not blog_text:
            return False

        subject_words = set(subject.split())
        category_words = set(category.split())
        content_words = set(blog_text.split())

        known_subjects = {
            "fox",
            "wolf",
            "dog",
            "cat",
            "lion",
            "tiger",
            "elephant",
            "bird",
            "horse",
            "deer",
            "bear",
        }

        image_subjects = subject_words & known_subjects
        mentioned_subjects = content_words & known_subjects

        if image_subjects and mentioned_subjects:
            if image_subjects.isdisjoint(mentioned_subjects):
                return True

        category_indicators = {
            "wildlife": {
                "fox", "wolf", "lion", "tiger", "elephant",
                "bird", "deer", "bear", "wildlife", "forest",
            },
            "food": {
                "food", "recipe", "cooking", "ingredient",
                "meal", "dish", "cuisine",
            },
            "technology": {
                "software", "computer", "technology", "programming",
                "hardware", "digital",
            },
            "travel": {
                "travel", "destination", "tourism", "journey",
                "hotel", "vacation",
            },
        }

        normalized_category = category
        category_terms = category_indicators.get(normalized_category)

        if category_terms:
            if not content_words.intersection(category_terms):
                return True

        return False

    @staticmethod
    def _cosine_similarity(
        vector_a: list[float],
        vector_b: list[float],
    ) -> float:
        if len(vector_a) != len(vector_b):
            raise ValueError("Embedding vectors must have equal dimensions.")

        if not vector_a:
            raise ValueError("Embedding vectors cannot be empty.")

        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        norm_a = math.sqrt(sum(value * value for value in vector_a))
        norm_b = math.sqrt(sum(value * value for value in vector_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def match(self, image: Any, blog_posts: list[Any]) -> dict:
        image_text = self._image_text(image)

        if not image_text:
            raise ValueError("Image metadata is required for matching.")

        if not blog_posts:
            return {
                "image_id": image.id,
                "status": "no_match",
                "reason": "No blog posts are available for matching.",
                "matches": [],
            }

        if (
            image.confidence is None
            or image.confidence < self.minimum_image_confidence
        ):
            return {
                "image_id": image.id,
                "status": "review_required",
                "reason": "Image confidence is too low for reliable matching.",
                "matches": [],
            }

        eligible_posts = [
            post
            for post in blog_posts
            if not self._has_explicit_mismatch(image, post)
        ]

        if not eligible_posts:
            return {
                "image_id": image.id,
                "status": "no_match",
                "reason": (
                    "All candidate blog posts were rejected by the "
                    "mismatch guard."
                ),
                "matches": [],
            }

        texts = [image_text]
        texts.extend(self._blog_text(post) for post in eligible_posts)

        embeddings = self.embedding_provider.embed(texts)

        if len(embeddings) != len(texts):
            raise ValueError(
                "Embedding provider returned an unexpected number of vectors."
            )

        image_embedding = embeddings[0]
        results = []

        for post, embedding in zip(eligible_posts, embeddings[1:]):
            similarity = self._cosine_similarity(
                image_embedding,
                embedding,
            )

            results.append(
                {
                    "blog_post_id": post.id,
                    "title": post.title,
                    "url": post.url,
                    "similarity": round(similarity, 6),
                    "reason": (
                        "Semantic similarity calculated from image metadata "
                        "and blog content."
                    ),
                }
            )

        results.sort(
            key=lambda item: item["similarity"],
            reverse=True,
        )

        accepted_matches = [
            result
            for result in results
            if result["similarity"] >= self.threshold
        ]

        if not accepted_matches:
            return {
                "image_id": image.id,
                "status": "no_match",
                "reason": (
                    "No eligible blog post reached the similarity threshold."
                ),
                "matches": results,
            }

        return {
            "image_id": image.id,
            "status": "matched",
            "reason": "Eligible blog posts ranked by semantic similarity.",
            "matches": accepted_matches,
        }
