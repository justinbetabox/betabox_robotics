"use strict";

import { elements } from "./dom.js";

import { clearBadgeClasses, formatBytes } from "./helpers.js";

export function renderStorage(storage) {
    const rawUsedPercent = Number(storage.used_percent);

    const hasUsedPercent = Number.isFinite(rawUsedPercent);

    const usedPercent = hasUsedPercent
        ? Math.min(100, Math.max(0, rawUsedPercent))
        : 0;

    clearBadgeClasses(elements.storagePercent);

    if (!hasUsedPercent) {
        elements.storagePercent.textContent = "Unknown";

        elements.storagePercent.classList.add("information-badge-neutral");
    } else {
        elements.storagePercent.textContent = `${usedPercent.toFixed(1)}% used`;

        if (usedPercent >= 95) {
            elements.storagePercent.classList.add("information-badge-error");
        } else if (usedPercent >= 85) {
            elements.storagePercent.classList.add("information-badge-warning");
        } else {
            elements.storagePercent.classList.add("information-badge-healthy");
        }
    }

    elements.storageMeterFill.style.width = `${usedPercent}%`;

    const track = elements.storageMeterFill.parentElement;

    if (track !== null) {
        track.setAttribute("aria-valuenow", String(Math.round(usedPercent)));
    }

    elements.storageUsed.textContent = formatBytes(storage.used_bytes);

    elements.storageAvailable.textContent = formatBytes(
        storage.available_bytes,
    );

    elements.storageTotal.textContent = formatBytes(storage.total_bytes);
}
