"use strict";

import { MEDIA_API_URL } from "./constants.js";

import { elements } from "./dom.js";

import { errorMessage, safeCount } from "./helpers.js";

import { renderMedia, updateSummary } from "./render.js";

import { state } from "./state.js";

import { announce, responseErrorMessage, setHidden } from "./utils.js";

function normalizeMediaFile(value) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
        return null;
    }

    const {
        category,
        name,
        media_type: mediaType,
        mime_type: mimeType,
        size_bytes: sizeBytes,
        modified_at: modifiedAt,
        url,
        download_url: downloadUrl,
    } = value;

    if (
        typeof category !== "string" ||
        typeof name !== "string" ||
        typeof mediaType !== "string" ||
        typeof mimeType !== "string" ||
        typeof url !== "string" ||
        typeof downloadUrl !== "string"
    ) {
        return null;
    }

    if (
        category !== "pictures" &&
        category !== "videos" &&
        category !== "sounds"
    ) {
        return null;
    }

    const normalizedSize = Number(sizeBytes);

    return {
        category,
        name,
        mediaType,
        mimeType,

        sizeBytes:
            Number.isFinite(normalizedSize) && normalizedSize >= 0
                ? normalizedSize
                : 0,

        modifiedAt: typeof modifiedAt === "string" ? modifiedAt : "",

        url,
        downloadUrl,
    };
}

function normalizeCounts(value) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
        return {
            pictures: 0,
            videos: 0,
            sounds: 0,
        };
    }

    return {
        pictures: safeCount(value.pictures),

        videos: safeCount(value.videos),

        sounds: safeCount(value.sounds),
    };
}

function normalizeMediaPayload(payload) {
    if (
        payload === null ||
        typeof payload !== "object" ||
        Array.isArray(payload)
    ) {
        throw new Error("The Media API returned an invalid response.");
    }

    const media = Array.isArray(payload.files)
        ? payload.files.map(normalizeMediaFile).filter((file) => file !== null)
        : [];

    const counts = normalizeCounts(payload.counts);

    const totalCount = safeCount(payload.total_count);

    const totalSizeBytes = Math.max(0, Number(payload.total_size_bytes) || 0);

    return {
        media,
        counts,
        totalCount,
        totalSizeBytes,
    };
}

function setLoading(loading) {
    state.loading = loading;

    setHidden(elements.loadingState, !loading || state.hasLoadedOnce);

    elements.refreshButton.disabled = loading;

    elements.refreshButton.textContent = loading ? "Refreshing…" : "Refresh";

    elements.retryButton.disabled = loading;
}

function showError(message) {
    setLoading(false);

    setHidden(elements.errorState, false);

    setHidden(elements.emptyState, true);

    setHidden(elements.items, true);

    elements.errorMessage.textContent = message;

    elements.resultSummary.textContent = "Media unavailable";
}

function hideError() {
    setHidden(elements.errorState, true);
}

function rebuildSummaryFromMedia() {
    const counts = {
        pictures: 0,
        videos: 0,
        sounds: 0,
    };

    let totalSizeBytes = 0;

    for (const file of state.media) {
        counts[file.category] += 1;

        totalSizeBytes += file.sizeBytes;
    }

    state.totalCount = state.media.length;

    state.counts = counts;

    state.totalSizeBytes = totalSizeBytes;
}

export async function loadMedia({ announceResult = true } = {}) {
    if (state.loading) {
        return;
    }

    hideError();

    if (!state.hasLoadedOnce) {
        setHidden(elements.emptyState, true);

        setHidden(elements.items, true);
    }

    setLoading(true);

    elements.resultSummary.textContent = "Loading media…";

    try {
        const response = await fetch(MEDIA_API_URL, {
            method: "GET",
            headers: {
                Accept: "application/json",
            },
            cache: "no-store",
        });

        if (!response.ok) {
            throw new Error(
                await responseErrorMessage(
                    response,
                    "Launchpad could not load media.",
                ),
            );
        }

        const normalized = normalizeMediaPayload(await response.json());

        state.media = normalized.media;

        state.counts = normalized.counts;

        state.totalCount = normalized.totalCount;

        state.totalSizeBytes = normalized.totalSizeBytes;

        /*
         * Treat the file collection itself as authoritative
         * for what is actually renderable on this page.
         */
        rebuildSummaryFromMedia();

        updateSummary();

        renderMedia();

        state.hasLoadedOnce = true;

        if (announceResult) {
            announce(
                `Loaded ${state.totalCount} ` +
                    (state.totalCount === 1 ? "media file" : "media files") +
                    ".",
            );
        }
    } catch (error) {
        showError(errorMessage(error, "Launchpad could not load media."));
    } finally {
        setLoading(false);
    }
}
