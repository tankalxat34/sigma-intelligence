import aiofiles
from fastapi import HTTPException, UploadFile, status
from pathlib import Path

ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",
    "video/mpeg",
    "video/x-matroska",
}

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB


def validate_content_type(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: mp4, webm, mov, avi, mpeg, mkv",
        )


async def save_upload_file(file: UploadFile, destination: Path) -> int:
    total = 0
    async with aiofiles.open(destination, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_FILE_SIZE_BYTES:
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // 1024 // 1024} MB",
                )
            await f.write(chunk)
    return total
