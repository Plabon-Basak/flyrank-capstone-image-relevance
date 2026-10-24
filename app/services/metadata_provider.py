
import asyncio

from google import genai
from google.genai import types
from PIL import Image

from app.core.config import settings
from app.schemas.image import ImageMetadata
from app.services.api_usage_tracker import APIUsageTracker


VISION_MAX_OUTPUT_TOKENS = 512


class MetadataProvider:
    async def generate_metadata(self, image_path: str) -> ImageMetadata:
        raise NotImplementedError


class MockMetadataProvider(MetadataProvider):
    async def generate_metadata(self, image_path: str) -> ImageMetadata:
        return ImageMetadata(
            subject="Image not analyzed",
            category="unclassified",
            attributes={
                "provider": "mock",
                "analysis_complete": False,
            },
            caption=(
                "Placeholder metadata from the mock provider. "
                "The image has not been analyzed by a vision model."
            ),
            confidence=0.0,
        )


class GeminiMetadataProvider(MetadataProvider):
    def __init__(
        self,
        client=None,
        usage_tracker=None,
        image_id=None,
    ):
        if client is None:
            if not settings.gemini_api_key.strip():
                raise ValueError(
                    "GEMINI_API_KEY is required for Gemini metadata analysis."
                )

            client = genai.Client(api_key=settings.gemini_api_key)

        self.client = client
        self.usage_tracker = usage_tracker
        self.image_id = image_id

    async def generate_metadata(self, image_path: str) -> ImageMetadata:
        prompt = """
Analyze this image for a blog image relevance and auto-tagging system.

Return valid JSON containing:
- subject: concise description of the main subject
- category: suitable general category
- attributes: visual details including dominant_colors, objects,
  setting, and visual_details
- caption: factual description of the image
- confidence: a number between 0 and 1

Do not invent details that cannot be visually verified.
Do not include provider or analysis status fields.
"""

        response_schema = ImageMetadata.model_json_schema()

        usage_id = None
        api_call_succeeded = False
        image = None

        try:
            with Image.open(image_path) as source_image:
                image = source_image.convert("RGB")

            contents = [prompt, image]
            input_tokens = None

            if self.usage_tracker is not None:
                count_response = await asyncio.to_thread(
                    self.client.models.count_tokens,
                    model=settings.gemini_vision_model,
                    contents=contents,
                )

                input_tokens = count_response.total_tokens

                if input_tokens is None:
                    raise ValueError(
                        "Gemini did not return an input token count."
                    )

                estimated_cost = APIUsageTracker.calculate_vision_cost(
                    input_tokens,
                    VISION_MAX_OUTPUT_TOKENS,
                )

                usage_id = self.usage_tracker.reserve(
                    model=settings.gemini_vision_model,
                    operation="vision",
                    estimated_cost_usd=estimated_cost,
                    image_id=self.image_id,
                )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=settings.gemini_vision_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    max_output_tokens=VISION_MAX_OUTPUT_TOKENS,
                ),
            )

            api_call_succeeded = True

            if usage_id is not None:
                usage_metadata = getattr(
                    response,
                    "usage_metadata",
                    None,
                )

                actual_input_tokens = getattr(
                    usage_metadata,
                    "prompt_token_count",
                    None,
                )

                actual_output_tokens = getattr(
                    usage_metadata,
                    "candidates_token_count",
                    None,
                )

                if (
                    actual_input_tokens is not None
                    and actual_output_tokens is not None
                ):
                    actual_cost = APIUsageTracker.calculate_vision_cost(
                        actual_input_tokens,
                        actual_output_tokens,
                    )

                    self.usage_tracker.complete(
                        usage_id,
                        input_tokens=actual_input_tokens,
                        output_tokens=actual_output_tokens,
                        estimated_cost_usd=actual_cost,
                        usage_source="provider",
                    )
                else:
                    self.usage_tracker.complete(
                        usage_id,
                        input_tokens=input_tokens,
                        output_tokens=VISION_MAX_OUTPUT_TOKENS,
                        usage_source="estimated",
                    )

            if not response.text:
                raise ValueError(
                    "Gemini returned an empty metadata response."
                )

            metadata = ImageMetadata.model_validate_json(response.text)

            attributes = dict(metadata.attributes)
            attributes["provider"] = "gemini"
            attributes["analysis_complete"] = True

            return metadata.model_copy(
                update={"attributes": attributes}
            )

        except Exception as exc:
            if usage_id is not None and not api_call_succeeded:
                try:
                    self.usage_tracker.fail(usage_id, str(exc))
                except Exception:
                    pass

            raise

        finally:
            if image is not None:
                image.close()


def get_metadata_provider(
    usage_tracker=None,
    image_id=None,
) -> MetadataProvider:
    provider_name = settings.metadata_provider.strip().lower()

    if provider_name == "mock":
        return MockMetadataProvider()

    if provider_name == "gemini":
        return GeminiMetadataProvider(
            usage_tracker=usage_tracker,
            image_id=image_id,
        )

    raise ValueError(
        "Unsupported metadata provider. Use gemini or mock."
    )
