"use strict";

function requireElement(selector, expectedType = HTMLElement) {
    const element = document.querySelector(selector);

    if (!(element instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return element;
}

function requireElements(selector, expectedType = HTMLElement) {
    const elements = Array.from(document.querySelectorAll(selector));

    if (elements.some((element) => !(element instanceof expectedType))) {
        throw new Error(`Invalid required elements: ${selector}`);
    }

    return elements;
}

export const elements = {
    refreshButton: requireElement("#media-refresh", HTMLButtonElement),

    retryButton: requireElement("#media-retry", HTMLButtonElement),

    totalCount: requireElement("#media-total-count"),

    pictureCount: requireElement("#media-picture-count"),

    videoCount: requireElement("#media-video-count"),

    soundCount: requireElement("#media-sound-count"),

    totalSize: requireElement("#media-total-size"),

    filterAllCount: requireElement("#media-filter-all-count"),

    filterPictureCount: requireElement("#media-filter-picture-count"),

    filterVideoCount: requireElement("#media-filter-video-count"),

    filterSoundCount: requireElement("#media-filter-sound-count"),

    resultSummary: requireElement("#media-result-summary"),

    categoryFilters: requireElements(
        "[data-media-category]",
        HTMLButtonElement,
    ),

    searchInput: requireElement("#media-search", HTMLInputElement),

    sortSelect: requireElement("#media-sort", HTMLSelectElement),

    gridViewButton: requireElement("#media-grid-view", HTMLButtonElement),

    listViewButton: requireElement("#media-list-view", HTMLButtonElement),

    loadingState: requireElement("#media-loading"),

    errorState: requireElement("#media-error"),

    errorMessage: requireElement("#media-error-message"),

    emptyState: requireElement("#media-empty"),

    emptyTitle: requireElement("#media-empty-title"),

    emptyMessage: requireElement("#media-empty-message"),

    items: requireElement("#media-items"),

    cardTemplate: requireElement("#media-card-template", HTMLTemplateElement),

    announcement: requireElement("#media-announcement"),

    previewDialog: requireElement("#media-preview-dialog", HTMLDialogElement),

    previewCloseButton: requireElement(
        "#media-preview-close",
        HTMLButtonElement,
    ),

    previewCategory: requireElement("#media-preview-category"),

    previewTitle: requireElement("#media-preview-title"),

    previewImage: requireElement("#media-preview-image", HTMLImageElement),

    previewVideo: requireElement("#media-preview-video", HTMLVideoElement),

    previewAudio: requireElement("#media-preview-audio", HTMLAudioElement),

    previewDate: requireElement("#media-preview-date"),

    previewSize: requireElement("#media-preview-size"),

    previewDownload: requireElement(
        "#media-preview-download",
        HTMLAnchorElement,
    ),

    deleteDialog: requireElement("#media-delete-dialog", HTMLDialogElement),

    deleteName: requireElement("#media-delete-name"),

    deleteError: requireElement("#media-delete-error"),

    deleteConfirmButton: requireElement(
        "#media-delete-confirm",
        HTMLButtonElement,
    ),

    uploadOpenButton: requireElement("#media-upload-open", HTMLButtonElement),

    uploadDialog: requireElement("#media-upload-dialog", HTMLDialogElement),

    uploadForm: requireElement("#media-upload-form", HTMLFormElement),

    uploadCloseButton: requireElement("#media-upload-close", HTMLButtonElement),

    uploadCancelButton: requireElement(
        "#media-upload-cancel",
        HTMLButtonElement,
    ),

    uploadConfirmButton: requireElement(
        "#media-upload-confirm",
        HTMLButtonElement,
    ),

    uploadInput: requireElement("#media-upload-input", HTMLInputElement),

    uploadDropzone: requireElement("#media-upload-dropzone"),

    uploadSelection: requireElement("#media-upload-selection"),

    uploadSelectionCount: requireElement("#media-upload-selection-count"),

    uploadFileList: requireElement("#media-upload-file-list", HTMLUListElement),

    uploadClearButton: requireElement("#media-upload-clear", HTMLButtonElement),

    uploadResult: requireElement("#media-upload-result"),

    uploadError: requireElement("#media-upload-error"),
};
