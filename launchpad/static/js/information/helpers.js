"use strict";

/* Formatting */

export function formatUpdatedTime(date) {
    return new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit",
        second: "2-digit",
    }).format(date);
}

export function displayValue(value, fallback = "Not available") {
    if (value === null || value === undefined || value === "") {
        return fallback;
    }

    return String(value);
}

export function formatBytes(value) {
    const bytes = Number(value);

    if (!Number.isFinite(bytes) || bytes < 0) {
        return "Not available";
    }

    if (bytes === 0) {
        return "0 B";
    }

    const units = ["B", "KB", "MB", "GB", "TB"];

    const unitIndex = Math.min(
        Math.floor(Math.log(bytes) / Math.log(1024)),
        units.length - 1,
    );

    const amount = bytes / Math.pow(1024, unitIndex);

    return `${amount.toFixed(
        amount >= 10 || unitIndex === 0 ? 0 : 1,
    )} ${units[unitIndex]}`;
}

/* Badges */

export function clearBadgeClasses(badge) {
    badge.classList.remove(
        "information-badge-healthy",
        "information-badge-warning",
        "information-badge-error",
        "information-badge-neutral",
    );
}

export function setAvailabilityBadge(
    badge,
    available,
    { availableLabel = "Available", unavailableLabel = "Unavailable" } = {},
) {
    clearBadgeClasses(badge);

    if (available === true) {
        badge.classList.add("information-badge-healthy");

        badge.textContent = availableLabel;

        return;
    }

    if (available === false) {
        badge.classList.add("information-badge-warning");

        badge.textContent = unavailableLabel;

        return;
    }

    badge.classList.add("information-badge-neutral");

    badge.textContent = "Unknown";
}
