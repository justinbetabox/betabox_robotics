from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

PREFERENCES_FILENAME: Final[str] = "appearance.json"

DEFAULT_PREFERENCES: Final[Mapping[str, object]] = MappingProxyType(
    {
        "theme": "system",
        "reduced_motion": False,
        "larger_text": False,
        "compact_layout": False,
    }
)

_ALLOWED_THEMES: Final[frozenset[str]] = frozenset(
    {
        "system",
        "light",
        "dark",
    }
)


def default_preferences() -> dict[str, object]:
    """Return a fresh copy of the default Launchpad preferences."""

    return dict(DEFAULT_PREFERENCES)


def preferences_path(
    preferences_directory: Path,
) -> Path:
    """Return the preference file within a workspace preference directory."""
    return preferences_directory / PREFERENCES_FILENAME


def validate_preferences(
    value: object,
) -> dict[str, object]:
    """Validate and normalize a Launchpad preference mapping."""

    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError("preferences must be a mapping")

    preferences_mapping = cast(
        Mapping[str, object],
        value,
    )

    theme = preferences_mapping.get("theme")

    if not isinstance(
        theme,
        str,
    ):
        raise TypeError("theme must be a string")

    if theme not in _ALLOWED_THEMES:
        raise ValueError("theme must be system, light, or dark")

    preferences: dict[str, object] = {
        "theme": theme,
    }

    for name in (
        "reduced_motion",
        "larger_text",
        "compact_layout",
    ):
        setting = preferences_mapping.get(name)

        if not isinstance(
            setting,
            bool,
        ):
            raise TypeError(f"{name} must be a boolean")

        preferences[name] = setting

    return preferences


def read_preferences(
    preferences_directory: Path,
) -> dict[str, object]:
    """Read preferences from a Launchpad workspace."""

    path = preferences_path(preferences_directory)

    if not path.exists():
        return default_preferences()

    payload = cast(
        object,
        json.loads(
            path.read_text(
                encoding="utf-8",
            )
        ),
    )

    return validate_preferences(payload)


def write_preferences(
    preferences_directory: Path,
    preferences: object,
) -> dict[str, object]:
    """Validate and atomically write Launchpad preferences."""

    values = validate_preferences(preferences)

    preferences_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = preferences_path(preferences_directory)

    temporary_path = path.with_name(f".{path.name}.tmp")

    try:
        _ = temporary_path.write_text(
            json.dumps(
                values,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        _ = temporary_path.replace(path)
    except OSError:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass

        raise

    return values


def reset_preferences(
    preferences_directory: Path,
) -> dict[str, object]:
    """Remove stored preferences and return the defaults."""

    path = preferences_path(preferences_directory)

    path.unlink(missing_ok=True)

    return default_preferences()
