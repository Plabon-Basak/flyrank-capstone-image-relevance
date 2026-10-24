
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.api_usage import APIUsage
from app.services.api_usage_tracker import (
    APIUsageTracker,
    BudgetExceededError,
    PricingNotConfiguredError,
)


@pytest.fixture
def database(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(
        "app.services.api_usage_tracker.settings.api_budget_usd",
        5.0,
    )

    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_vision_cost_calculation(monkeypatch):
    monkeypatch.setattr(
        "app.services.api_usage_tracker.settings.gemini_vision_input_cost_per_million_tokens",
        1.0,
    )
    monkeypatch.setattr(
        "app.services.api_usage_tracker.settings.gemini_vision_output_cost_per_million_tokens",
        2.0,
    )

    cost = APIUsageTracker.calculate_vision_cost(1000, 2000)

    assert cost == Decimal("0.005")


def test_embedding_cost_calculation(monkeypatch):
    monkeypatch.setattr(
        "app.services.api_usage_tracker.settings.gemini_embedding_cost_per_million_characters",
        0.5,
    )

    cost = APIUsageTracker.calculate_embedding_cost(10000)

    assert cost == Decimal("0.005")


def test_vision_cost_requires_configured_rates(monkeypatch):
    monkeypatch.setattr(
        "app.services.api_usage_tracker.settings.gemini_vision_input_cost_per_million_tokens",
        0.0,
    )

    with pytest.raises(PricingNotConfiguredError):
        APIUsageTracker.calculate_vision_cost(1000, 1000)


def test_embedding_cost_requires_configured_rate(monkeypatch):
    monkeypatch.setattr(
        "app.services.api_usage_tracker.settings.gemini_embedding_cost_per_million_characters",
        0.0,
    )

    with pytest.raises(PricingNotConfiguredError):
        APIUsageTracker.calculate_embedding_cost(1000)


def test_reserve_creates_usage_record(database):
    with database() as db:
        tracker = APIUsageTracker(db)

        usage_id = tracker.reserve(
            model="gemini-test",
            operation="embedding",
            estimated_cost_usd=Decimal("0.50"),
        )

        usage = db.get(APIUsage, usage_id)

        assert usage is not None
        assert usage.status == "reserved"
        assert usage.provider == "gemini"
        assert usage.estimated_cost_usd == Decimal("0.50000000")


def test_reserve_rejects_over_budget(database):
    with database() as db:
        tracker = APIUsageTracker(db)

        tracker.reserve(
            model="gemini-test",
            operation="embedding",
            estimated_cost_usd=Decimal("4.00"),
        )

        with pytest.raises(BudgetExceededError):
            tracker.reserve(
                model="gemini-test",
                operation="embedding",
                estimated_cost_usd=Decimal("2.00"),
            )

        records = db.scalars(select(APIUsage)).all()

        assert len(records) == 1


def test_complete_reconciles_usage(database):
    with database() as db:
        tracker = APIUsageTracker(db)

        usage_id = tracker.reserve(
            model="gemini-test",
            operation="embedding",
            estimated_cost_usd=Decimal("0.50"),
        )

        tracker.complete(
            usage_id,
            billable_characters=10000,
            estimated_cost_usd=Decimal("0.25"),
            usage_source="provider",
        )

        usage = db.get(APIUsage, usage_id)

        assert usage.status == "succeeded"
        assert usage.billable_characters == 10000
        assert usage.estimated_cost_usd == Decimal("0.25000000")
        assert usage.usage_source == "provider"


def test_fail_preserves_reservation(database):
    with database() as db:
        tracker = APIUsageTracker(db)

        usage_id = tracker.reserve(
            model="gemini-test",
            operation="vision",
            estimated_cost_usd=Decimal("0.50"),
        )

        tracker.fail(usage_id, "Test API failure")

        usage = db.get(APIUsage, usage_id)

        assert usage.status == "failed"
        assert usage.error_message == "Test API failure"
        assert usage.estimated_cost_usd == Decimal("0.50000000")
