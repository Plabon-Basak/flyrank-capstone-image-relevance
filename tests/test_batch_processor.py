
import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.batch_job import BatchJob
from app.models.image import Image
from app.schemas.image import ImageMetadata
from app.services.batch_processor import process_batch_job


@pytest.fixture
def database():
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

    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def add_image(db, file_path, filename="fox.jpg"):
    image = Image(
        filename=filename,
        file_path=str(file_path),
        subject="Original subject",
        category="wildlife",
        attributes={"animal": "fox"},
        caption="Original caption",
        confidence=0.8,
        status="pending",
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def add_job(db, image_ids, max_retries=1):
    job = BatchJob(
        image_ids=image_ids,
        total_items=len(image_ids),
        max_retries=max_retries,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class FakeMetadataProvider:
    async def generate_metadata(self, image_path):
        return ImageMetadata(
            subject="Red fox",
            category="wildlife",
            attributes={"animal": "fox", "provider": "fake"},
            caption="A red fox in a forest.",
            confidence=0.97,
        )


def test_process_batch_job_success(database, tmp_path, monkeypatch):
    image_path = tmp_path / "fox.jpg"
    image_path.write_bytes(b"test image")

    with database() as db:
        image = add_image(db, image_path)
        job = add_job(db, [image.id])
        job_id = job.id
        image_id = image.id

    monkeypatch.setattr(
        "app.services.batch_processor.get_metadata_provider",
        lambda: FakeMetadataProvider(),
    )

    process_batch_job(job_id, database)

    with database() as db:
        job = db.get(BatchJob, job_id)
        image = db.get(Image, image_id)

        assert job.status == "completed"
        assert job.total_items == 1
        assert job.processed_items == 1
        assert job.failed_items == 0
        assert job.completed_at is not None
        assert image.subject == "Red fox"
        assert image.caption == "A red fox in a forest."
        assert image.confidence == 0.97
        assert image.status == "completed"


def test_process_batch_job_retries_missing_file(database, tmp_path, monkeypatch):
    missing_path = tmp_path / "missing.jpg"

    with database() as db:
        image = add_image(db, missing_path)
        job = add_job(db, [image.id], max_retries=2)
        job_id = job.id
        image_id = image.id

    monkeypatch.setattr(
        "app.services.batch_processor.get_metadata_provider",
        lambda: FakeMetadataProvider(),
    )

    process_batch_job(job_id, database)

    with database() as db:
        job = db.get(BatchJob, job_id)

        assert job.status == "failed"
        assert job.processed_items == 0
        assert job.failed_items == 1
        assert job.retry_count == 2
        assert str(image_id) in job.error_details
        assert "could not be found" in job.error_details[str(image_id)]


def test_process_batch_job_rejects_mock_metadata(
    database,
    tmp_path,
    monkeypatch,
):
    image_path = tmp_path / "fox.jpg"
    image_path.write_bytes(b"test image")

    class MockProvider:
        async def generate_metadata(self, image_path):
            return ImageMetadata(
                subject="Image not analyzed",
                category="unclassified",
                attributes={"provider": "mock"},
                caption="Placeholder metadata.",
                confidence=0.0,
            )

    with database() as db:
        image = add_image(db, image_path)
        job = add_job(db, [image.id], max_retries=0)
        job_id = job.id
        image_id = image.id

    monkeypatch.setattr(
        "app.services.batch_processor.get_metadata_provider",
        lambda: MockProvider(),
    )

    process_batch_job(job_id, database)

    with database() as db:
        job = db.get(BatchJob, job_id)
        image = db.get(Image, image_id)

        assert job.status == "failed"
        assert job.failed_items == 1
        assert job.processed_items == 0
        assert image.subject == "Original subject"
        assert image.status == "pending"
        assert "not real image analysis" in job.error_details[str(image_id)]
