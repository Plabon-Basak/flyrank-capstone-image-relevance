
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import BatchJob


def test_batch_job_default_values():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as db:
            job = BatchJob()
            db.add(job)
            db.commit()
            db.refresh(job)

            assert job.id is not None
            assert job.status == "pending"
            assert job.total_items == 0
            assert job.processed_items == 0
            assert job.failed_items == 0
            assert job.retry_count == 0
            assert job.max_retries == 3
            assert job.estimated_cost_usd == 0.0
            assert job.error_details is None
            assert job.last_error is None
            assert job.created_at is not None
            assert job.started_at is None
            assert job.completed_at is None
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_batch_job_tracks_progress_and_failure_details():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as db:
            job = BatchJob(
                status="processing",
                total_items=10,
                processed_items=6,
                failed_items=1,
                retry_count=2,
                estimated_cost_usd=0.004,
                error_details={"image_7": "Temporary provider error"},
                last_error="Temporary provider error",
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            assert job.status == "processing"
            assert job.total_items == 10
            assert job.processed_items == 6
            assert job.failed_items == 1
            assert job.retry_count == 2
            assert job.estimated_cost_usd == 0.004
            assert job.error_details == {
                "image_7": "Temporary provider error"
            }
            assert job.last_error == "Temporary provider error"
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
