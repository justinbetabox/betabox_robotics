from __future__ import annotations

from html import escape


def back_link(
    *,
    href: str = "/",
    label: str = "Launchpad",
    css_class: str = "back-link",
) -> str:
    return f"""
<a
    class="{escape(css_class)}"
    href="{escape(href)}"
>
    ← {escape(label)}
</a>
""".strip()


def page_heading(
    *,
    eyebrow: str,
    title: str,
) -> str:
    return f"""
<div class="page-heading">
    <p class="eyebrow">
        {escape(eyebrow)}
    </p>

    <h1 class="page-title">
        {escape(title)}
    </h1>
</div>
""".strip()


def status_pill(
    *,
    element_id: str,
    text: str,
    css_class: str,
) -> str:
    return f"""
<div
    id="{escape(element_id)}"
    class="{escape(css_class)}"
    role="status"
    aria-live="polite"
    aria-atomic="true"
>
    {escape(text)}
</div>
""".strip()


def action_card(
    *,
    title: str,
    description: str,
    href: str,
    category: str,
    accent: str = "blue",
    action: str = "Open",
    css_class: str = "",
) -> str:
    classes = " ".join(
        value
        for value in (
            "action-card",
            f"accent-{accent}",
            css_class,
        )
        if value
    )

    return f"""
<a
    class="{escape(classes)}"
    href="{escape(href)}"
>
    <span class="action-card-category">
        {escape(category)}
    </span>

    <h3>{escape(title)}</h3>

    <p>{escape(description)}</p>

    <div class="action-card-footer">
        <span>{escape(action)}</span>

        <span
            class="action-card-arrow"
            aria-hidden="true"
        >
            →
        </span>
    </div>
</a>
""".strip()
