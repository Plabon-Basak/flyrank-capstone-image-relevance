from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.services.image_storage import save_uploaded_image


def make_image_bytes(image_format="PNG"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(
        buffer,
        format=image_format,
    )
    return buffer.getvalue()


def make_upload(content, filename="test.png"):
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
    )


@pytest.mark.anyio
async def test_saves_valid_png(tmp_path):
    upload = make_upload(make_image_bytes("PNG"))

    filename, file_path = await save_uploaded_image(
        upload,
        str(tmp_path),
        1024 * 1024,
    )

    assert filename.endswith(".png")
    assert (tmp_path / filename).is_file()
    assert file_path.endswith(filename)


@pytest.mark.anyio
async def test_rejects_empty_file(tmp_path):
    upload = make_upload(b"")

    with pytest.raises(HTTPException) as exc:
        await save_uploaded_image(upload, str(tmp_path), 1024)

    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_rejects_invalid_image(tmp_path):
    upload = make_upload(b"this is not an image")

    with pytest.raises(HTTPException) as exc:
        await save_uploaded_image(upload, str(tmp_path), 1024)

    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_rejects_unsupported_format(tmp_path):
    upload = make_upload(make_image_bytes("BMP"), "test.bmp")

    with pytest.raises(HTTPException) as exc:
        await save_uploaded_image(upload, str(tmp_path), 1024 * 1024)

    assert exc.value.status_code == 415


@pytest.mark.anyio
async def test_rejects_oversized_upload(tmp_path):
    upload = make_upload(make_image_bytes("PNG"))

    with pytest.raises(HTTPException) as exc:
        await save_uploaded_image(upload, str(tmp_path), 10)

    assert exc.value.status_code == 413


@pytest.mark.anyio
async def test_generates_unique_filenames(tmp_path):
    content = make_image_bytes("PNG")

    first = await save_uploaded_image(
        make_upload(content),
        str(tmp_path),
        1024 * 1024,
    )
    second = await save_uploaded_image(
        make_upload(content),
        str(tmp_path),
        1024 * 1024,
    )

    assert first[0] != second[0]
    assert (tmp_path / first[0]).is_file()
    assert (tmp_path / second[0]).is_file()
