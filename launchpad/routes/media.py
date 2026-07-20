from __future__ import annotations

import mimetypes

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import aiohttp_jinja2

from aiohttp import web

from betabox_robotics.config import PlatformConfig


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


def category_directories(
    config: PlatformConfig,
) -> dict[str, Path]:
    return {
        "pictures": config.paths.pictures_dir,
        "videos": config.paths.videos_dir,
        "sounds": config.paths.sounds_dir,
    }


def require_category(
    config: PlatformConfig,
    category: str,
) -> Path:
    directory = category_directories(
        config
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
                "main_class": (
                    "content-container "
                    "page-content "
                    "media-page"
                ),
            },
        },
    )


async def media_api(
    request: web.Request,
) -> web.Response:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    requested_category = request.query.get(
        "category"
    )

    directories = category_directories(
        config
    )

    if requested_category is not None:
        directory = require_category(
            config,
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


async def media_file(
    request: web.Request,
) -> web.StreamResponse:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    category = request.match_info[
        "category"
    ]

    filename = request.match_info[
        "filename"
    ]

    directory = require_category(
        config,
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
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    category = request.match_info[
        "category"
    ]

    filename = request.match_info[
        "filename"
    ]

    directory = require_category(
        config,
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
