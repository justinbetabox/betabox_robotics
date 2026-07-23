from __future__ import annotations

import mimetypes

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiohttp_jinja2

from aiohttp import web

from betabox_robotics.launchpad.auth import (
    LaunchpadContext,
    Workspace
)


MEDIA_EXTENSIONS: dict[str, frozenset[str]] = {
    "pictures": frozenset(
        {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }
    ),
    "videos": frozenset(
        {
            ".mp4",
            ".webm",
        }
    ),
    "sounds": frozenset(
        {
            ".mp3",
            ".wav",
            ".ogg",
            ".m4a",
        }
    ),
}

MEDIA_TYPES: dict[str, str] = {
    "pictures": "image",
    "videos": "video",
    "sounds": "audio",
}

UPLOAD_CATEGORIES = frozenset(
    {
        "pictures",
        "sounds",
    }
)

MAX_UPLOAD_FILES = 10

MAX_UPLOAD_FILE_SIZE = (
    25
    * 1024
    * 1024
)

UPLOAD_CHUNK_SIZE = (
    64
    * 1024
)


@dataclass(frozen=True)
class MediaItem:
    category: str
    name: str
    media_type: str
    mime_type: str
    size_bytes: int
    modified_at: str
    url: str
    download_url: str

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "category": self.category,
            "name": self.name,
            "media_type": self.media_type,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at,
            "url": self.url,
            "download_url": self.download_url,
        }

@dataclass(frozen=True)
class MediaUploadFailure:
    name: str
    reason: str

    def to_dict(
        self,
    ) -> dict[str, str]:
        return {
            "name": self.name,
            "reason": self.reason,
        }

def category_directories(
    workspace: Workspace,
) -> dict[str, Path]:
    return {
        "pictures": workspace.media.pictures,
        "videos": workspace.media.videos,
        "sounds": workspace.media.sounds,
    }


def require_category(
    workspace: Workspace,
    category: str,
) -> Path:
    directory = category_directories(
        workspace
    ).get(category)

    if directory is None:
        raise web.HTTPNotFound(
            reason="media category not found"
        )

    return directory


def validate_filename(
    filename: str,
) -> None:
    if not filename:
        raise web.HTTPBadRequest(
            reason="media filename cannot be empty"
        )

    if filename.startswith("."):
        raise web.HTTPBadRequest(
            reason=(
                "hidden media files are not available"
            )
        )

    if (
        Path(filename).name != filename
        or "/" in filename
        or "\\" in filename
    ):
        raise web.HTTPBadRequest(
            reason="invalid media filename"
        )


def resolve_media_file(
    directory: Path,
    filename: str,
) -> Path:
    validate_filename(
        filename
    )

    root = directory.resolve()
    candidate = root / filename

    if candidate.is_symlink():
        raise web.HTTPNotFound(
            reason="media file not found"
        )

    try:
        resolved = candidate.resolve(
            strict=True
        )
    except FileNotFoundError as exc:
        raise web.HTTPNotFound(
            reason="media file not found"
        ) from exc
    except OSError as exc:
        raise web.HTTPNotFound(
            reason="media file not found"
        ) from exc

    if resolved.parent != root:
        raise web.HTTPBadRequest(
            reason="invalid media filename"
        )

    if not resolved.is_file():
        raise web.HTTPNotFound(
            reason="media file not found"
        )

    return resolved


def media_extension_allowed(
    category: str,
    path: Path,
) -> bool:
    allowed_extensions = MEDIA_EXTENSIONS.get(
        category
    )

    if allowed_extensions is None:
        return False

    return (
        path.suffix.lower()
        in allowed_extensions
    )

def upload_category(
    filename: str,
) -> str | None:
    suffix = Path(filename).suffix.lower()

    for category in UPLOAD_CATEGORIES:
        if (
            suffix
            in MEDIA_EXTENSIONS[category]
        ):
            return category

    return None

def upload_rejection_reason(
    filename: str,
) -> str:
    suffix = Path(filename).suffix.lower()

    if (
        suffix
        in MEDIA_EXTENSIONS["videos"]
    ):
        return "Videos cannot be uploaded."

    if not suffix:
        return (
            "The file does not have a supported "
            "extension."
        )

    return (
        "Only JPG, JPEG, PNG, WebP, MP3, WAV, "
        "OGG, and M4A files can be uploaded."
    )

def upload_content_type_allowed(
    category: str,
    content_type: str | None,
) -> bool:
    if not content_type:
        return True

    normalized = (
        content_type
        .split(
            ";",
            maxsplit=1,
        )[0]
        .strip()
        .lower()
    )

    if (
        normalized
        in {
            "",
            "application/octet-stream",
        }
    ):
        return True

    if category == "pictures":
        return normalized.startswith(
            "image/"
        )

    if category == "sounds":
        return (
            normalized.startswith(
                "audio/"
            )
            or normalized
            in {
                "application/ogg",
            }
        )

    return False

def media_mime_type(
    path: Path,
) -> str:
    mime_type, _ = mimetypes.guess_type(
        path.name
    )

    return (
        mime_type
        or "application/octet-stream"
    )


def media_url(
    category: str,
    filename: str,
    *,
    download: bool = False,
) -> str:
    encoded_category = quote(
        category,
        safe="",
    )

    encoded_filename = quote(
        filename,
        safe="",
    )

    url = (
        f"/api/media/"
        f"{encoded_category}/"
        f"{encoded_filename}"
    )

    if download:
        return f"{url}?download=1"

    return url


def build_media_item(
    category: str,
    path: Path,
) -> MediaItem:
    stat = path.stat()

    modified_at = datetime.fromtimestamp(
        stat.st_mtime
    ).astimezone().isoformat()

    return MediaItem(
        category=category,
        name=path.name,
        media_type=MEDIA_TYPES[category],
        mime_type=media_mime_type(path),
        size_bytes=stat.st_size,
        modified_at=modified_at,
        url=media_url(
            category,
            path.name,
        ),
        download_url=media_url(
            category,
            path.name,
            download=True,
        ),
    )

def unique_media_path(
    directory: Path,
    filename: str,
) -> Path:
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    original = Path(filename)

    stem = original.stem
    suffix = original.suffix.lower()

    candidate = (
        directory
        / f"{stem}{suffix}"
    )

    if not candidate.exists():
        return candidate

    sequence = 2

    while True:
        candidate = (
            directory
            / f"{stem}-{sequence}{suffix}"
        )

        if not candidate.exists():
            return candidate

        sequence += 1

async def save_uploaded_file(
    field: Any,
    destination: Path,
) -> int:
    bytes_written = 0

    temporary_path = destination.with_name(
        f".{destination.name}.uploading"
    )

    try:
        with temporary_path.open("xb") as output:
            while True:
                chunk = await field.read_chunk(
                    size=UPLOAD_CHUNK_SIZE
                )

                if not chunk:
                    break

                bytes_written += len(chunk)

                if (
                    bytes_written
                    > MAX_UPLOAD_FILE_SIZE
                ):
                    raise ValueError(
                        "The file exceeds the "
                        "25 MB upload limit."
                    )

                output.write(chunk)

        if bytes_written == 0:
            raise ValueError(
                "The uploaded file is empty."
            )

        temporary_path.replace(
            destination
        )

        return bytes_written
    except BaseException:
        try:
            temporary_path.unlink(
                missing_ok=True
            )
        except OSError:
            pass

        raise

def upload_failure(
    failures: list[MediaUploadFailure],
    filename: str,
    reason: str,
) -> None:
    failures.append(
        MediaUploadFailure(
            name=(
                filename
                or "Unnamed file"
            ),
            reason=reason,
        )
    )

def list_category_media(
    category: str,
    directory: Path,
) -> list[MediaItem]:
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    items: list[MediaItem] = []

    try:
        paths = tuple(
            directory.iterdir()
        )
    except OSError:
        return items

    for path in paths:
        if (
            path.name.startswith(".")
            or path.is_symlink()
            or not path.is_file()
            or not media_extension_allowed(
                category,
                path,
            )
        ):
            continue

        try:
            item = build_media_item(
                category,
                path,
            )
        except OSError:
            continue

        items.append(
            item
        )

    items.sort(
        key=lambda item: item.modified_at,
        reverse=True,
    )

    return items


async def media_page(
    request: web.Request,
) -> web.Response:
    return aiohttp_jinja2.render_template(
        "media.html",
        request,
        {
            "page": {
                "title": "Media",
                "eyebrow": "Robot Files",
                "main_class": "page-layout media-page"
            },
        },
    )


async def media_api(
    request: web.Request,
) -> web.Response:
    context: LaunchpadContext = request[
        "launchpad_context"
    ]

    workspace = context.workspace

    requested_category = request.query.get(
        "category"
    )

    directories = category_directories(
        workspace
    )

    if requested_category is not None:
        directory = require_category(
            workspace,
            requested_category,
        )

        selected_directories = {
            requested_category: directory,
        }
    else:
        selected_directories = directories

    items: list[MediaItem] = []

    for category, directory in (
        selected_directories.items()
    ):
        items.extend(
            list_category_media(
                category,
                directory,
            )
        )

    items.sort(
        key=lambda item: item.modified_at,
        reverse=True,
    )

    counts = {
        category: 0
        for category in MEDIA_EXTENSIONS
    }

    total_size_bytes = 0

    for item in items:
        counts[item.category] += 1
        total_size_bytes += item.size_bytes

    return web.json_response(
        {
            "files": [
                item.to_dict()
                for item in items
            ],
            "counts": counts,
            "total_count": len(items),
            "total_size_bytes": (
                total_size_bytes
            ),
        }
    )

async def upload_media(
    request: web.Request,
) -> web.Response:
    context: LaunchpadContext = request[
        "launchpad_context"
    ]

    workspace = context.workspace

    if not request.content_type.startswith(
        "multipart/"
    ):
        raise web.HTTPBadRequest(
            reason=(
                "media uploads must use "
                "multipart form data"
            )
        )

    try:
        reader = await request.multipart()
    except (ValueError, OSError) as exc:
        raise web.HTTPBadRequest(
            reason=(
                "the upload request could not "
                "be read"
            )
        ) from exc

    uploaded: list[MediaItem] = []

    failures: list[
        MediaUploadFailure
    ] = []

    submitted_files = 0

    while True:
        try:
            field = await reader.next()
        except (ValueError, OSError) as exc:
            raise web.HTTPBadRequest(
                reason=(
                    "the upload request could not "
                    "be read"
                )
            ) from exc

        if field is None:
            break

        if (
            field.name != "files"
            or not field.filename
        ):
            continue

        submitted_files += 1

        original_filename = Path(
            field.filename
        ).name

        if (
            submitted_files
            > MAX_UPLOAD_FILES
        ):
            upload_failure(
                failures,
                original_filename,
                (
                    "Only 10 files can be "
                    "uploaded at once."
                ),
            )

            continue

        try:
            validate_filename(
                original_filename
            )
        except web.HTTPException as exc:
            upload_failure(
                failures,
                original_filename,
                exc.reason
                or "Invalid media filename.",
            )

            continue

        category = upload_category(
            original_filename
        )

        if category is None:
            upload_failure(
                failures,
                original_filename,
                upload_rejection_reason(
                    original_filename
                ),
            )

            continue

        if not upload_content_type_allowed(
            category,
            field.headers.get(
                "Content-Type"
            ),
        ):
            upload_failure(
                failures,
                original_filename,
                (
                    "The file type does not match "
                    "its extension."
                ),
            )

            continue

        directory = require_category(
            workspace,
            category,
        )

        destination = unique_media_path(
            directory,
            original_filename,
        )

        if not media_extension_allowed(
            category,
            destination,
        ):
            upload_failure(
                failures,
                original_filename,
                "Unsupported media format.",
            )

            continue

        try:
            await save_uploaded_file(
                field,
                destination,
            )

            uploaded.append(
                build_media_item(
                    category,
                    destination,
                )
            )
        except ValueError as exc:
            upload_failure(
                failures,
                original_filename,
                str(exc),
            )
        except FileExistsError:
            upload_failure(
                failures,
                original_filename,
                (
                    "A temporary upload with this "
                    "name already exists."
                ),
            )
        except OSError:
            upload_failure(
                failures,
                original_filename,
                (
                    "The file could not be saved "
                    "on the robot."
                ),
            )

    if submitted_files == 0:
        raise web.HTTPBadRequest(
            reason=(
                "the upload does not contain "
                "any files"
            )
        )

    status = (
        201
        if uploaded
        else 400
    )

    return web.json_response(
        {
            "uploaded": [
                item.to_dict()
                for item in uploaded
            ],
            "failed": [
                failure.to_dict()
                for failure in failures
            ],
            "uploaded_count": len(
                uploaded
            ),
            "failed_count": len(
                failures
            ),
        },
        status=status,
    )

async def media_file(
    request: web.Request,
) -> web.StreamResponse:
    context: LaunchpadContext = request[
        "launchpad_context"
    ]

    workspace = context.workspace

    category = request.match_info[
        "category"
    ]

    filename = request.match_info[
        "filename"
    ]

    directory = require_category(
        workspace,
        category,
    )

    path = resolve_media_file(
        directory,
        filename,
    )

    if not media_extension_allowed(
        category,
        path,
    ):
        raise web.HTTPNotFound(
            reason="media file not found"
        )

    response = web.FileResponse(
        path
    )

    response.content_type = media_mime_type(
        path
    )

    if request.query.get("download") == "1":
        encoded_filename = quote(
            path.name,
            safe="",
        )

        response.headers[
            "Content-Disposition"
        ] = (
            "attachment; "
            f"filename*=UTF-8''"
            f"{encoded_filename}"
        )

    return response


async def delete_media_file(
    request: web.Request,
) -> web.Response:
    context: LaunchpadContext = request[
        "launchpad_context"
    ]

    workspace = context.workspace

    category = request.match_info[
        "category"
    ]

    filename = request.match_info[
        "filename"
    ]

    directory = require_category(
        workspace,
        category,
    )

    path = resolve_media_file(
        directory,
        filename,
    )

    if not media_extension_allowed(
        category,
        path,
    ):
        raise web.HTTPNotFound(
            reason="media file not found"
        )

    try:
        path.unlink()
    except FileNotFoundError as exc:
        raise web.HTTPNotFound(
            reason="media file not found"
        ) from exc
    except OSError as exc:
        raise web.HTTPInternalServerError(
            reason=(
                "media file could not be deleted"
            )
        ) from exc

    return web.json_response(
        {
            "deleted": True,
            "category": category,
            "name": filename,
        }
    )


def setup_media_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/media",
        media_page,
        name="media-page",
    )

    app.router.add_get(
        "/api/media",
        media_api,
        name="media-api",
    )

    app.router.add_post(
        "/api/media/upload",
        upload_media,
        name="media-upload-api",
    )

    app.router.add_get(
        "/api/media/{category}/{filename}",
        media_file,
        name="media-file",
    )

    app.router.add_delete(
        "/api/media/{category}/{filename}",
        delete_media_file,
        name="media-delete-api",
    )
