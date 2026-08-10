"use strict";

import { elements } from "./dom.js";

import {
    filteredFiles,
    updateFilterButtons,
    updateViewButtons,
} from "./filters.js";

import {
    categoryLabel,
    formatBytes,
    formatDate,
    pluralize,
} from "./helpers.js";

import { openDeleteDialog } from "./delete.js";

import { openPreview } from "./preview.js";

import { state } from "./state.js";

import { configureThumbnail } from "./thumbnails.js";

import { setHidden } from "./utils.js";

export function updateSummary() {
    const pictureCount = state.counts.pictures ?? 0;

    const videoCount = state.counts.videos ?? 0;

    const soundCount = state.counts.sounds ?? 0;

    elements.totalCount.textContent = String(state.totalCount);

    elements.pictureCount.textContent = String(pictureCount);

    elements.videoCount.textContent = String(videoCount);

    elements.soundCount.textContent = String(soundCount);

    elements.totalSize.textContent = formatBytes(state.totalSizeBytes);

    elements.filterAllCount.textContent = String(state.totalCount);

    elements.filterPictureCount.textContent = String(pictureCount);

    elements.filterVideoCount.textContent = String(videoCount);

    elements.filterSoundCount.textContent = String(soundCount);
}

function updateResultSummary(visibleCount) {
    const hasFilter = state.category !== "all" || state.search.trim() !== "";

    if (!hasFilter) {
        elements.resultSummary.textContent =
            `${visibleCount} ` + pluralize(visibleCount, "file", "files");

        return;
    }

    elements.resultSummary.textContent =
        `${visibleCount} of ` +
        `${state.totalCount} ` +
        pluralize(state.totalCount, "file", "files");
}

function updateEmptyState(visibleCount) {
    const hasAnyMedia = state.totalCount > 0;

    const hasSearch = state.search.trim() !== "";

    const hasCategoryFilter = state.category !== "all";

    if (visibleCount > 0) {
        setHidden(elements.emptyState, true);

        setHidden(elements.items, false);

        return;
    }

    setHidden(elements.items, true);

    setHidden(elements.emptyState, false);

    if (hasAnyMedia && (hasSearch || hasCategoryFilter)) {
        elements.emptyTitle.textContent = "No matching media";

        elements.emptyMessage.textContent =
            "Try another search or choose " + "a different media category.";

        return;
    }

    elements.emptyTitle.textContent = "No media yet";

    elements.emptyMessage.textContent =
        "Pictures, recordings, and sounds " +
        "created on this robot will appear here.";
}

function createMediaCard(file) {
    const fragment = elements.cardTemplate.content.cloneNode(true);

    const card = fragment.querySelector(".media-card");

    const previewButton = fragment.querySelector(".media-preview-button");

    const image = fragment.querySelector(".media-thumbnail-image");

    const video = fragment.querySelector(".media-thumbnail-video");

    const placeholder = fragment.querySelector(".media-thumbnail-placeholder");

    const placeholderIcon = fragment.querySelector(".media-placeholder-icon");

    const typeLabel = fragment.querySelector(".media-type-label");

    const playIndicator = fragment.querySelector(".media-play-indicator");

    const name = fragment.querySelector(".media-card-name");

    const date = fragment.querySelector(".media-card-date");

    const size = fragment.querySelector(".media-card-size");

    const downloadButton = fragment.querySelector(".media-download-button");

    const deleteButton = fragment.querySelector(".media-delete-button");

    if (
        !(card instanceof HTMLElement) ||
        !(previewButton instanceof HTMLButtonElement) ||
        !(image instanceof HTMLImageElement) ||
        !(video instanceof HTMLVideoElement) ||
        !(placeholder instanceof HTMLElement) ||
        !(placeholderIcon instanceof HTMLElement) ||
        !(typeLabel instanceof HTMLElement) ||
        !(playIndicator instanceof HTMLElement) ||
        !(name instanceof HTMLElement) ||
        !(date instanceof HTMLElement) ||
        !(size instanceof HTMLElement) ||
        !(downloadButton instanceof HTMLAnchorElement) ||
        !(deleteButton instanceof HTMLButtonElement)
    ) {
        throw new Error("Media card template is invalid.");
    }

    card.dataset.mediaCategory = file.category;

    name.textContent = file.name;

    name.title = file.name;

    date.textContent = formatDate(file.modifiedAt);

    size.textContent = formatBytes(file.sizeBytes);

    typeLabel.textContent = categoryLabel(file.category);

    previewButton.setAttribute("aria-label", `Preview ${file.name}`);

    previewButton.addEventListener("click", () => {
        openPreview(file);
    });

    downloadButton.href = file.downloadUrl;

    downloadButton.setAttribute("aria-label", `Download ${file.name}`);

    deleteButton.setAttribute("aria-label", `Delete ${file.name}`);

    deleteButton.addEventListener("click", () => {
        openDeleteDialog(file);
    });

    configureThumbnail(file, {
        image,
        video,
        placeholder,
        placeholderIcon,
        playIndicator,
    });

    return fragment;
}

export function renderMedia() {
    const files = filteredFiles();

    elements.items.replaceChildren();

    const fragment = document.createDocumentFragment();

    for (const file of files) {
        fragment.append(createMediaCard(file));
    }

    elements.items.append(fragment);

    updateFilterButtons();

    updateViewButtons();

    updateResultSummary(files.length);

    updateEmptyState(files.length);
}
