"use strict";

import { loadMedia } from "./api.js";

import {
    closeDeleteDialog,
    deleteSelectedFile,
    resetDeleteDialog,
} from "./delete.js";

import { elements } from "./dom.js";

import {
    setCategory,
    setSearch,
    setSort,
    setView,
    updateViewButtons,
} from "./filters.js";

import { closePreview, resetPreview } from "./preview.js";

import { renderMedia } from "./render.js";

import { state } from "./state.js";

import {
    closeUploadDialog,
    openUploadDialog,
    resetUploadDialog,
    updateUploadSelection,
    uploadMedia,
} from "./upload.js";

import { announce } from "./utils.js";

function configureLibraryControls() {
    elements.refreshButton.addEventListener("click", () => {
        void loadMedia();
    });

    elements.retryButton.addEventListener("click", () => {
        void loadMedia();
    });

    for (const button of elements.categoryFilters) {
        button.addEventListener("click", () => {
            const category = button.dataset.mediaCategory ?? "all";

            if (!setCategory(category)) {
                return;
            }

            renderMedia();

            announce(
                category === "all"
                    ? "Showing all media."
                    : `Showing ${category}.`,
            );
        });
    }

    elements.searchInput.addEventListener("input", () => {
        setSearch(elements.searchInput.value);

        renderMedia();
    });

    elements.sortSelect.addEventListener("change", () => {
        if (!setSort(elements.sortSelect.value)) {
            return;
        }

        renderMedia();
    });

    elements.gridViewButton.addEventListener("click", () => {
        if (!setView("grid")) {
            return;
        }

        announce("Grid view enabled.");
    });

    elements.listViewButton.addEventListener("click", () => {
        if (!setView("list")) {
            return;
        }

        announce("List view enabled.");
    });
}

function configurePreviewDialog() {
    elements.previewCloseButton.addEventListener("click", closePreview);

    elements.previewDialog.addEventListener("close", resetPreview);

    elements.previewDialog.addEventListener("click", (event) => {
        if (event.target === elements.previewDialog) {
            closePreview();
        }
    });
}

function configureDeleteDialog() {
    elements.deleteDialog.addEventListener("close", resetDeleteDialog);

    elements.deleteDialog.addEventListener("click", (event) => {
        if (event.target === elements.deleteDialog) {
            closeDeleteDialog();
        }
    });

    elements.deleteConfirmButton.addEventListener("click", () => {
        void deleteSelectedFile({
            reloadMedia: loadMedia,
        });
    });
}

function configureUploadDialog() {
    elements.uploadOpenButton.addEventListener("click", openUploadDialog);

    elements.uploadCloseButton.addEventListener("click", closeUploadDialog);

    elements.uploadCancelButton.addEventListener("click", closeUploadDialog);

    elements.uploadInput.addEventListener("change", updateUploadSelection);

    elements.uploadClearButton.addEventListener("click", () => {
        elements.uploadInput.value = "";

        updateUploadSelection();
    });

    elements.uploadForm.addEventListener("submit", (event) => {
        void uploadMedia(event, {
            reloadMedia: loadMedia,
        });
    });

    elements.uploadDialog.addEventListener("cancel", (event) => {
        if (state.uploading) {
            event.preventDefault();

            return;
        }

        resetUploadDialog();
    });

    elements.uploadDialog.addEventListener("close", resetUploadDialog);

    elements.uploadDialog.addEventListener("click", (event) => {
        if (event.target === elements.uploadDialog) {
            closeUploadDialog();
        }
    });
}

export function initializeMediaPage() {
    configureLibraryControls();

    configurePreviewDialog();

    configureDeleteDialog();

    configureUploadDialog();

    updateViewButtons();

    void loadMedia();
}
