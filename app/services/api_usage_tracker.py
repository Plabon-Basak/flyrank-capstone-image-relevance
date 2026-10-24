
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.api_usage import APIUsage


GEMINI_VISION_OPERATION = "vision"
GEMINI_EMBEDDING_OPERATION = "embedding"
GEMINI_OPERATIONS = frozenset(
    {
        GEMINI_VISION_OPERATION,
        GEMINI_EMBEDDING_OPERATION,
    }
)


class BudgetExceededError(Exception):
    pass


class PricingNotConfiguredError(Exception):
    pass


class APIUsageTracker:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _decimal(value: float | int | Decimal) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Invalid cost or pricing value.")

    @classmethod
    def _validated_vision_rates(cls) -> tuple[Decimal, Decimal]:
        input_rate = cls._decimal(
            settings.gemini_vision_input_cost_per_million_tokens
        )
        output_rate = cls._decimal(
            settings.gemini_vision_output_cost_per_million_tokens
        )

        if input_rate <= 0 or output_rate <= 0:
            raise PricingNotConfiguredError(
                "Gemini Vision pricing is not configured. Set "
                "GEMINI_VISION_INPUT_COST_PER_MILLION_TOKENS and "
                "GEMINI_VISION_OUTPUT_COST_PER_MILLION_TOKENS "
                "to positive values."
            )

        return input_rate, output_rate

    @classmethod
    def _validated_embedding_rate(cls) -> Decimal:
        rate = cls._decimal(
            settings.gemini_embedding_cost_per_million_characters
        )

        if rate <= 0:
            raise PricingNotConfiguredError(
                "Gemini embedding pricing is not configured. Set "
                "GEMINI_EMBEDDING_COST_PER_MILLION_CHARACTERS "
                "to a positive value."
            )

        return rate

    @classmethod
    def _validated_budget(cls) -> Decimal:
        budget = cls._decimal(settings.api_budget_usd)

        if budget <= 0:
            raise PricingNotConfiguredError(
                "Gemini API budget is not configured. Set "
                "API_BUDGET_USD to a positive value."
            )

        return budget

    @classmethod
    def preflight(cls, operations: Iterable[str]) -> None:
        """Validate pricing and budget before paid Gemini operations."""
        requested = tuple(dict.fromkeys(operations))
        unsupported = set(requested) - GEMINI_OPERATIONS

        if unsupported:
            raise ValueError(
                "Unsupported Gemini operation(s): "
                + ", ".join(sorted(unsupported))
                + "."
            )

        if not requested:
            return

        for operation in requested:
            if operation == GEMINI_VISION_OPERATION:
                cls._validated_vision_rates()
            elif operation == GEMINI_EMBEDDING_OPERATION:
                cls._validated_embedding_rate()

        cls._validated_budget()

    @staticmethod
    def calculate_vision_cost(
        input_tokens: int,
        output_tokens: int,
    ) -> Decimal:
        input_rate, output_rate = APIUsageTracker._validated_vision_rates()

        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("Token counts cannot be negative.")

        return (
            Decimal(input_tokens) * input_rate
            + Decimal(output_tokens) * output_rate
        ) / Decimal(1_000_000)

    @staticmethod
    def calculate_embedding_cost(billable_characters: int) -> Decimal:
        rate = APIUsageTracker._validated_embedding_rate()

        if billable_characters < 0:
            raise ValueError("Billable characters cannot be negative.")

        return (
            Decimal(billable_characters) * rate
        ) / Decimal(1_000_000)

    def reserve(
        self,
        *,
        model: str,
        operation: str,
        estimated_cost_usd: Decimal,
        image_id: int | None = None,
        blog_post_id: int | None = None,
    ) -> int:
        amount = self._decimal(estimated_cost_usd)

        if amount <= 0:
            raise ValueError("Reservation must be greater than zero.")

        budget = self._validated_budget()

        try:
            if self.db.bind.dialect.name == "postgresql":
                self.db.execute(
                    text("SELECT pg_advisory_xact_lock(840613)")
                )

            current_total = self.db.scalar(
                select(func.coalesce(func.sum(APIUsage.estimated_cost_usd), 0))
                .where(
                    APIUsage.status.in_(
                        ["reserved", "succeeded", "failed"]
                    )
                )
            )

            current_total = self._decimal(current_total or 0)

            if current_total + amount > budget:
                raise BudgetExceededError(
                    f"API budget exceeded. "
                    f"Used/reserved: ${current_total:.8f}; "
                    f"requested: ${amount:.8f}; "
                    f"budget: ${budget:.8f}."
                )

            usage = APIUsage(
                provider="gemini",
                model=model,
                operation=operation,
                image_id=image_id,
                blog_post_id=blog_post_id,
                usage_source="estimated",
                estimated_cost_usd=amount,
                status="reserved",
            )

            self.db.add(usage)
            self.db.commit()
            self.db.refresh(usage)

            return usage.id

        except Exception:
            self.db.rollback()
            raise

    def complete(
        self,
        usage_id: int,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        billable_characters: int | None = None,
        estimated_cost_usd: Decimal | None = None,
        usage_source: str = "provider",
    ) -> None:
        usage = self.db.get(APIUsage, usage_id)

        if usage is None:
            raise ValueError("API usage record was not found.")

        if usage.status != "reserved":
            raise ValueError("Only reserved usage records can be completed.")

        if estimated_cost_usd is not None:
            actual_cost = self._decimal(estimated_cost_usd)
            if actual_cost < 0:
                raise ValueError("Cost cannot be negative.")
            usage.estimated_cost_usd = actual_cost

        usage.input_tokens = input_tokens
        usage.output_tokens = output_tokens
        usage.billable_characters = billable_characters
        usage.usage_source = usage_source
        usage.status = "succeeded"

        self.db.commit()

    def fail(self, usage_id: int, error_message: str) -> None:
        usage = self.db.get(APIUsage, usage_id)

        if usage is None:
            raise ValueError("API usage record was not found.")

        if usage.status != "reserved":
            raise ValueError("Only reserved usage records can be failed.")

        usage.status = "failed"
        usage.error_message = error_message[:2000]
        self.db.commit()
