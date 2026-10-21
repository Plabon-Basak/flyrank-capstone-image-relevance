
from collections.abc import Generator

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.image import Image
from app.schemas.image import ImageCreate, ImageRead

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
