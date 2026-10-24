from app.core.config import settings
from app.db.session import SessionLocal
from app.models.blog_post import BlogPost
from app.models.image import Image
from app.services.embedding_factory import get_embedding_provider
from app.services.embedding_text import (
    blog_embedding_text,
    generate_embedding,
    image_embedding_text,
)


def main():
    if settings.embedding_provider.strip().lower() != "gemini":
        raise RuntimeError(
            "Set EMBEDDING_PROVIDER=gemini before running the backfill."
        )

    provider = get_embedding_provider()
    db = SessionLocal()

    image_count = 0
    post_count = 0
    skipped_count = 0

    try:
        images = db.query(Image).order_by(Image.id).all()

        for image in images:
            if image.embedding is not None:
                continue

            if image.status != "completed":
                skipped_count += 1
                continue

            text = image_embedding_text(image)

            if not text:
                skipped_count += 1
                continue

            image.embedding = generate_embedding(provider, text)
            db.commit()
            image_count += 1
            print(f"Image {image.id}: embedding saved")

        posts = db.query(BlogPost).order_by(BlogPost.id).all()

        for post in posts:
            if post.embedding is not None:
                continue

            text = blog_embedding_text(post)

            if not text:
                skipped_count += 1
                continue

            post.embedding = generate_embedding(provider, text)
            db.commit()
            post_count += 1
            print(f"Blog post {post.id}: embedding saved")

        print("\nBackfill completed.")
        print(f"Image embeddings created: {image_count}")
        print(f"Blog post embeddings created: {post_count}")
        print(f"Records skipped: {skipped_count}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
