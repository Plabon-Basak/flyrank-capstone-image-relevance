from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image as PILImage
from PIL import UnidentifiedImageError


SUPPORTED_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}


async def save_uploaded_image(
    upload: UploadFile,
    upload_dir: str,
    max_size_bytes: int,
) -> tuple[str, str]:
    directory = Path(upload_dir)
    directory.mkdir(parents=True, exist_ok=True)

    file_id = uuid4().hex
    temporary_path = directory / f"{file_id}.upload"
    size = 0

    try:
        with temporary_path.open("wb") as destination:
            while True:
                chunk = await upload.read(1024 * 1024)

                if not chunk:
                    break

                size += len(chunk)

                if size > max_size_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="Image exceeds the maximum upload size.",
                    )

                destination.write(chunk)

        if size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        try:
            with PILImage.open(temporary_path) as image:
                image_format = image.format

                if image_format not in SUPPORTED_FORMATS:
                    raise HTTPException(
                        status_code=415,
                        detail="Only JPEG, PNG, and WebP images are supported.",
                    )

                image.verify()

        except HTTPException:
            raise
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is not a valid image.",
            ) from exc

        filename = f"{file_id}{SUPPORTED_FORMATS[image_format]}"
        final_path = directory / filename
        temporary_path.replace(final_path)

        return filename, final_path.as_posix()

    finally:
        if temporary_path.exists():
            temporary_path.unlink()
