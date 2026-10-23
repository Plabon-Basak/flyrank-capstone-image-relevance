from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.batch_job import BatchJob
from app.models.blog_post import BlogPost
from app.models.image import Image
from app.models.match_suggestion import MatchSuggestion
from app.schemas.batch_job import BatchJobCreate, BatchJobRead
from app.schemas.blog_post import BlogPostCreate, BlogPostRead
from app.schemas.image import ImageCreate, ImageRead
from app.schemas.match_suggestion import (
    MatchSuggestionRead,
    MatchSuggestionReview,
)
from app.services.batch_processor import process_batch_job
from app.services.confidence_review import requires_review
from app.services.embedding_provider import (
    LexicalEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from app.services.image_storage import save_uploaded_image
from app.services.match_suggestion_service import save_match_suggestions
from app.services.matching_service import MatchingService
from app.services.metadata_provider import get_metadata_provider


app = FastAPI(
    title="Image Relevance & Auto-Tagging Engine",
    description="API for image understanding and semantic content matching.",
    version="0.1.0",
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/images",
    response_model=ImageRead,
    status_code=status.HTTP_201_CREATED,
)
def create_image(
    image_data: ImageCreate,
    db: Session = Depends(get_db),
):
    image = Image(**image_data.model_dump(), status="pending")
    db.add(image)

    try:
        db.commit()
        db.refresh(image)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An image with this filename already exists.",
        ) from exc

    return image


@app.post(
    "/images/upload",
    response_model=ImageRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    filename, file_path = await save_uploaded_image(
        file,
        settings.upload_dir,
        max_size_bytes,
    )

    image = Image(
        filename=filename,
        file_path=file_path,
        status="pending",
    )
    db.add(image)

    try:
        db.commit()
        db.refresh(image)
    except IntegrityError as exc:
        db.rollback()
        Path(file_path).unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An image with this filename already exists.",
        ) from exc
    except Exception:
        db.rollback()
        Path(file_path).unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    return image


@app.get("/images", response_model=list[ImageRead])
def list_images(db: Session = Depends(get_db)):
    return db.query(Image).order_by(Image.id).all()


@app.get("/images/{image_id}", response_model=ImageRead)
def get_image(image_id: int, db: Session = Depends(get_db)):
    image = db.get(Image, image_id)

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )

    return image


@app.post("/images/{image_id}/analyze")
async def analyze_image(
    image_id: int,
    db: Session = Depends(get_db),
):
    image = db.get(Image, image_id)

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )

    if not Path(image.file_path).is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The image file could not be found on disk.",
        )

    try:
        provider = get_metadata_provider()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The configured metadata provider is unavailable.",
        ) from exc

    try:
        metadata = await provider.generate_metadata(image.file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image metadata analysis failed.",
        ) from exc

    if metadata.attributes.get("provider") == "mock":
        return {
            "image_id": image.id,
            "status": "mock_analysis",
            "message": (
                "Placeholder metadata generated. "
                "No real image analysis was performed. "
                "Existing database metadata was not changed."
            ),
            "metadata": metadata.model_dump(),
        }

    try:
        image.subject = metadata.subject
        image.category = metadata.category
        image.attributes = metadata.attributes
        image.caption = metadata.caption
        image.confidence = metadata.confidence
        image.review_required = requires_review(metadata.confidence)
        image.status = "completed"

        db.commit()
        db.refresh(image)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis results could not be saved.",
        ) from exc

    return {
        "image_id": image.id,
        "status": "analysis_completed",
        "review_required": image.review_required,
        "metadata": metadata.model_dump(),
    }




@app.get("/images/{image_id}/matches")
def match_image_to_blog_posts(
    image_id: int,
    db: Session = Depends(get_db),
):
    image = db.get(Image, image_id)

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )

    provider_name = settings.embedding_provider.strip().lower()

    try:
        if provider_name == "openai":
            if not settings.embedding_api_key.strip():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "OpenAI embeddings require EMBEDDING_API_KEY "
                        "to be configured."
                    ),
                )
            embedding_provider = OpenAIEmbeddingProvider()
        elif provider_name == "lexical":
            embedding_provider = LexicalEmbeddingProvider()
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Semantic matching is not configured. Set "
                    "EMBEDDING_PROVIDER=lexical for the local text baseline or "
                    "EMBEDDING_PROVIDER=openai and configure EMBEDDING_API_KEY "
                    "for OpenAI embeddings."
                ),
            )

        blog_posts = (
            db.query(BlogPost)
            .order_by(BlogPost.id)
            .all()
        )

        matching_service = MatchingService(
            embedding_provider=embedding_provider,
            threshold=settings.matching_threshold,
        )

        result = matching_service.match(image, blog_posts)

        saved_suggestions = save_match_suggestions(
            db=db,
            image_id=image.id,
            matches=result.get("matches", []),
        )

        result["matches"] = [
            {
                **match,
                "suggestion_id": suggestion.id,
                "review_status": suggestion.status,
            }
            for match, suggestion in zip(
                result.get("matches", []),
                saved_suggestions,
                strict=True,
            )
        ]

        if provider_name == "lexical":
            result["matching_method"] = "lexical_baseline"
            result["matching_notice"] = (
                "Uses text-token statistics, not neural embeddings "
                "or image pixel understanding."
            )

        return result

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc



@app.post(
    "/blog-posts",
    response_model=BlogPostRead,
    status_code=status.HTTP_201_CREATED,
)
def create_blog_post(
    post_data: BlogPostCreate,
    db: Session = Depends(get_db),
):
    post = BlogPost(**post_data.model_dump())
    db.add(post)

    try:
        db.commit()
        db.refresh(post)
    except Exception:
        db.rollback()
        raise

    return post


@app.get("/blog-posts", response_model=list[BlogPostRead])
def list_blog_posts(db: Session = Depends(get_db)):
    return db.query(BlogPost).order_by(BlogPost.id).all()


@app.get("/blog-posts/{post_id}", response_model=BlogPostRead)
def get_blog_post(
    post_id: int,
    db: Session = Depends(get_db),
):
    post = db.get(BlogPost, post_id)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found.",
        )

    return post


@app.post(
    "/batch-jobs",
    response_model=BatchJobRead,
    status_code=status.HTTP_201_CREATED,
)
def create_batch_job(
    job_data: BatchJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    images = (
        db.query(Image)
        .filter(Image.id.in_(job_data.image_ids))
        .all()
    )

    found_ids = {image.id for image in images}
    missing_ids = [
        image_id
        for image_id in job_data.image_ids
        if image_id not in found_ids
    ]

    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "One or more images were not found.",
                "missing_image_ids": missing_ids,
            },
        )

    job = BatchJob(
        image_ids=job_data.image_ids,
        total_items=len(job_data.image_ids),
        max_retries=job_data.max_retries,
        status="pending",
    )

    db.add(job)

    try:
        db.commit()
        db.refresh(job)
        job_id = job.id
    except Exception:
        db.rollback()
        raise

    background_tasks.add_task(process_batch_job, job_id)

    return job


@app.get(
    "/batch-jobs/{job_id}",
    response_model=BatchJobRead,
)
def get_batch_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    job = db.get(BatchJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch job not found.",
        )

    return job

@app.get(
    "/match-suggestions",
    response_model=list[MatchSuggestionRead],
)
def list_match_suggestions(
    review_status: str | None = None,
    db: Session = Depends(get_db),
):
    if review_status is not None and review_status not in {
        "pending",
        "approved",
        "rejected",
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid review status.",
        )

    query = db.query(MatchSuggestion)

    if review_status is not None:
        query = query.filter(MatchSuggestion.status == review_status)

    return query.order_by(MatchSuggestion.id).all()


@app.post(
    "/match-suggestions/{suggestion_id}/review",
    response_model=MatchSuggestionRead,
)
def review_match_suggestion(
    suggestion_id: int,
    review: MatchSuggestionReview,
    db: Session = Depends(get_db),
):
    suggestion = db.get(MatchSuggestion, suggestion_id)

    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match suggestion not found.",
        )

    if suggestion.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This suggestion has already been reviewed and "
                "cannot be changed."
            ),
        )

    suggestion.status = review.status
    suggestion.decision_reason = review.decision_reason
    suggestion.reviewed_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(suggestion)
    except Exception:
        db.rollback()
        raise

    return suggestion
