
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.batch_job import BatchJob
from app.models.image import Image
from app.services.confidence_review import requires_review
from app.services.metadata_provider import get_metadata_provider


def process_batch_job(
    job_id: int,
    session_factory: sessionmaker = SessionLocal,
) -> None:
    db: Session = session_factory()

    try:
        job = db.get(BatchJob, job_id)

        if job is None or job.status != "pending":
            return

        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        job.last_error = None
        job.error_details = {}
        db.commit()

        try:
            provider = get_metadata_provider()
        except ValueError as exc:
            job.status = "failed"
            job.last_error = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        errors = dict(job.error_details or {})

        for image_id in job.image_ids:
            image = db.get(Image, image_id)

            if image is None:
                job.failed_items += 1
                errors[str(image_id)] = "Image no longer exists."
                job.error_details = errors
                job.last_error = errors[str(image_id)]
                db.commit()
                continue

            succeeded = False
            last_error = None

            for attempt in range(job.max_retries + 1):
                try:
                    if not Path(image.file_path).is_file():
                        raise FileNotFoundError(
                            "Image file could not be found on disk."
                        )

                    import asyncio

                    metadata = asyncio.run(
                        provider.generate_metadata(image.file_path)
                    )

                    if metadata.attributes.get("provider") == "mock":
                        raise ValueError(
                            "Mock metadata is not real image analysis."
                        )

                    image.subject = metadata.subject
                    image.category = metadata.category
                    image.attributes = metadata.attributes
                    image.caption = metadata.caption
                    image.confidence = metadata.confidence
                    image.review_required = requires_review(
                        metadata.confidence
                    )
                    image.status = "completed"

                    succeeded = True
                    break

                except Exception as exc:
                    last_error = str(exc)

                    if attempt < job.max_retries:
                        job.retry_count += 1
                        db.commit()

            if succeeded:
                job.processed_items += 1
                errors.pop(str(image_id), None)
            else:
                job.failed_items += 1
                errors[str(image_id)] = last_error or "Unknown processing error."
                job.last_error = errors[str(image_id)]

            job.error_details = errors
            db.commit()

        job.status = (
            "completed" if job.failed_items == 0 else "failed"
        )
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        db.rollback()

        job = db.get(BatchJob, job_id)
        if job is not None:
            job.status = "failed"
            job.last_error = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

    finally:
        db.close()
