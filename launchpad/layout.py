from __future__ import annotations

from html import escape
from typing import Iterable


def unique_paths(
    paths: Iterable[str],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(paths)
    )


def stylesheet_tags(
    stylesheets: Iterable[str],
) -> str:
    return "\n".join(
        f"""
    <link
        rel="stylesheet"
        href="{escape(path)}"
    >""".rstrip()
        for path in stylesheets
    )


def script_tags(
    scripts: Iterable[str],
) -> str:
    return "\n".join(
        f"""
    <script src="{escape(path)}"></script>
""".rstrip()
        for path in scripts
    )


def module_script_tags(
    scripts: Iterable[str],
) -> str:
    return "\n".join(
        f"""
    <script
        type="module"
        src="{escape(path)}"
    ></script>
""".rstrip()
        for path in scripts
    )


def render_page(
    *,
    title: str,
    body: str,
    body_class: str = "",
    stylesheets: Iterable[str] = (),
    scripts: Iterable[str] = (),
    module_scripts: Iterable[str] = (),
) -> str:
    all_stylesheets = unique_paths(
        (
            "/static/tokens.css",
            "/static/components.css",
            *stylesheets,
        )
    )

    all_scripts = unique_paths(
        (
            "/static/theme.js",
            *scripts,
        )
    )

    all_module_scripts = unique_paths(module_scripts)

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>{escape(title)}</title>

{stylesheet_tags(all_stylesheets)}
</head>

<body class="{escape(body_class)}">
{body}

{script_tags(all_scripts)}
{module_script_tags(all_module_scripts)}
</body>
</html>
"""
