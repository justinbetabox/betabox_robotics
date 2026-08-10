"use strict";

import { elements } from "./dom.js";

import { categoryLabel, formatBytes, formatDate } from "./helpers.js";

import { state } from "./state.js";

import { setHidden } from "./utils.js";

export function stopPreviewMedia() {
    elements.previewVideo.pause();

    elements.previewVideo.removeAttribute("src");

    elements.previewVideo.load();

    elements.previewAudio.pause();

    elements.previewAudio.removeAttribute("src");

    elements.previewAudio.load();

    elements.previewImage.removeAttribute("src");

    elements.previewImage.alt = "";

    setHidden(elements.previewImage, true);

    setHidden(elements.previewVideo, true);

    setHidden(elements.previewAudio, true);
}

export function openPreview(file) {
    stopPreviewMedia();

    state.previewFile = file;

    elements.previewCategory.textContent = categoryLabel(file.category);

    elements.previewTitle.textContent = file.name;

    elements.previewDate.textContent = formatDate(file.modifiedAt);

    elements.previewSize.textContent = formatBytes(file.sizeBytes);

    elements.previewDownload.href = file.downloadUrl;

    elements.previewDownload.setAttribute(
        "aria-label",
        `Download ${file.name}`,
    );

    switch (file.category) {
        case "pictures":
            elements.previewImage.src = file.url;

            elements.previewImage.alt = file.name;

            setHidden(elements.previewImage, false);

            break;

        case "videos":
            elements.previewVideo.src = file.url;

            setHidden(elements.previewVideo, false);

            break;

        case "sounds":
            elements.previewAudio.src = file.url;

            setHidden(elements.previewAudio, false);

            break;

        default:
            state.previewFile = null;

            return;
    }

    elements.previewDialog.showModal();
}

export function closePreview() {
    if (elements.previewDialog.open) {
        elements.previewDialog.close();
    }

    stopPreviewMedia();

    state.previewFile = null;
}

export function resetPreview() {
    stopPreviewMedia();

    state.previewFile = null;
}
