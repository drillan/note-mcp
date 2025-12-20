"""Image upload operations for note.com API.

Provides functionality for uploading images to note.com.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from note_mcp.api.client import NoteAPIClient
from note_mcp.models import ErrorCode, Image, NoteAPIError, Session

if TYPE_CHECKING:
    pass


# Allowed image file extensions
ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Maximum file size in bytes (10MB)
MAX_FILE_SIZE: int = 10 * 1024 * 1024


def validate_image_file(file_path: str) -> None:
    """Validate image file before upload.

    Args:
        file_path: Path to the image file

    Raises:
        NoteAPIError: If file is invalid (not found, wrong format, too large)
    """
    path = Path(file_path)

    # Check file exists
    if not path.exists():
        raise NoteAPIError(
            code=ErrorCode.INVALID_INPUT,
            message=f"File not found: {file_path}",
            details={"file_path": file_path},
        )

    # Check file extension
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise NoteAPIError(
            code=ErrorCode.INVALID_INPUT,
            message=(f"Invalid file format: {path.suffix}. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"),
            details={"file_path": file_path, "extension": path.suffix},
        )

    # Check file size
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise NoteAPIError(
            code=ErrorCode.INVALID_INPUT,
            message=(f"File size ({file_size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)"),
            details={"file_path": file_path, "size": file_size, "max_size": MAX_FILE_SIZE},
        )


async def upload_image(
    session: Session,
    file_path: str,
    note_id: str | None = None,
) -> Image:
    """Upload an image to note.com.

    Validates the file format and size before uploading.
    Uses multipart/form-data for the upload.

    Note: note.com requires a note_id for image uploads.
    This endpoint uploads as an eyecatch (header) image.

    Args:
        session: Authenticated session
        file_path: Path to the image file
        note_id: The note ID to associate the image with (required by API)

    Returns:
        Image object with upload result

    Raises:
        NoteAPIError: If validation fails or API request fails
    """
    # Validate file before upload
    validate_image_file(file_path)

    if note_id is None:
        raise NoteAPIError(
            code=ErrorCode.INVALID_INPUT,
            message="note_id is required for image upload",
            details={"file_path": file_path},
        )

    path = Path(file_path)
    file_size = path.stat().st_size

    # Prepare file for multipart upload
    with open(file_path, "rb") as f:
        file_content = f.read()

    # Determine content type based on extension
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    content_type = content_types.get(path.suffix.lower(), "application/octet-stream")

    # Prepare files for multipart request
    files = {
        "file": (path.name, file_content, content_type),
    }

    # note_id is required by the API
    data = {"note_id": note_id}

    async with NoteAPIClient(session) as client:
        response = await client.post("/v1/image_upload/note_eyecatch", files=files, data=data)

    # Parse response
    image_data = response.get("data", {})

    return Image(
        key=image_data.get("key", ""),
        url=image_data.get("url", ""),
        original_path=file_path,
        size_bytes=file_size,
        uploaded_at=int(time.time()),
    )
