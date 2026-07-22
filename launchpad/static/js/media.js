"use strict";


/* Constants */
const MEDIA_API_URL = "/api/media";

const MEDIA_UPLOAD_API_URL = (
    "/api/media/upload"
);

const MAX_UPLOAD_FILES = 10;

const MAX_UPLOAD_FILE_SIZE = (
    25
    * 1024
    * 1024
);

const UPLOAD_EXTENSIONS = new Set([
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp3",
    ".wav",
    ".ogg",
    ".m4a",
]);

const VIDEO_EXTENSIONS = new Set([
    ".mp4",
    ".webm",
]);

const CATEGORY_LABELS = {
    pictures: "Picture",
    videos: "Video",
    sounds: "Sound",
};


/* Page state */

const state = {
    media: [],
    counts: {
        pictures: 0,
        videos: 0,
        sounds: 0,
    },
    totalCount: 0,
    totalSizeBytes: 0,
    category: "all",
    search: "",
    sort: "newest",
    view: "grid",
    previewFile: null,
    deleteFile: null,
    loading: false,
    uploading: false,
};


/* DOM */

function requireElement(
    selector
) {
    const element = document.querySelector(
        selector
    );

    if (element === null) {
        throw new Error(
            `Missing required element: ${selector}`
        );
    }

    return element;
}

const elements = {
    refreshButton: requireElement(
        "#media-refresh"
    ),
    retryButton: requireElement(
        "#media-retry"
    ),

    totalCount: requireElement(
        "#media-total-count"
    ),
    pictureCount: requireElement(
        "#media-picture-count"
    ),
    videoCount: requireElement(
        "#media-video-count"
    ),
    soundCount: requireElement(
        "#media-sound-count"
    ),
    totalSize: requireElement(
        "#media-total-size"
    ),

    filterAllCount: requireElement(
        "#media-filter-all-count"
    ),
    filterPictureCount: requireElement(
        "#media-filter-picture-count"
    ),
    filterVideoCount: requireElement(
        "#media-filter-video-count"
    ),
    filterSoundCount: requireElement(
        "#media-filter-sound-count"
    ),

    resultSummary: requireElement(
        "#media-result-summary"
    ),
    categoryFilters: Array.from(
        document.querySelectorAll(
            "[data-media-category]"
        )
    ),
    searchInput: requireElement(
        "#media-search"
    ),
    sortSelect: requireElement(
        "#media-sort"
    ),

    gridViewButton: requireElement(
        "#media-grid-view"
    ),
    listViewButton: requireElement(
        "#media-list-view"
    ),

    loadingState: requireElement(
        "#media-loading"
    ),
    errorState: requireElement(
        "#media-error"
    ),
    errorMessage: requireElement(
        "#media-error-message"
    ),
    emptyState: requireElement(
        "#media-empty"
    ),
    emptyTitle: requireElement(
        "#media-empty-title"
    ),
    emptyMessage: requireElement(
        "#media-empty-message"
    ),
    items: requireElement(
        "#media-items"
    ),
    cardTemplate: requireElement(
        "#media-card-template"
    ),
    announcement: requireElement(
        "#media-announcement"
    ),

    previewDialog: requireElement(
        "#media-preview-dialog"
    ),
    previewCloseButton: requireElement(
        "#media-preview-close"
    ),
    previewCategory: requireElement(
        "#media-preview-category"
    ),
    previewTitle: requireElement(
        "#media-preview-title"
    ),
    previewImage: requireElement(
        "#media-preview-image"
    ),
    previewVideo: requireElement(
        "#media-preview-video"
    ),
    previewAudio: requireElement(
        "#media-preview-audio"
    ),
    previewDate: requireElement(
        "#media-preview-date"
    ),
    previewSize: requireElement(
        "#media-preview-size"
    ),
    previewDownload: requireElement(
        "#media-preview-download"
    ),

    deleteDialog: requireElement(
        "#media-delete-dialog"
    ),
    deleteName: requireElement(
        "#media-delete-name"
    ),
    deleteError: requireElement(
        "#media-delete-error"
    ),
    deleteConfirmButton: requireElement(
        "#media-delete-confirm"
    ),
    uploadOpenButton: requireElement(
        "#media-upload-open"
    ),
    uploadDialog: requireElement(
        "#media-upload-dialog"
    ),
    uploadForm: requireElement(
        "#media-upload-form"
    ),
    uploadCloseButton: requireElement(
        "#media-upload-close"
    ),
    uploadCancelButton: requireElement(
        "#media-upload-cancel"
    ),
    uploadConfirmButton: requireElement(
        "#media-upload-confirm"
    ),
    uploadInput: requireElement(
        "#media-upload-input"
    ),
    uploadDropzone: requireElement(
        "#media-upload-dropzone"
    ),
    uploadSelection: requireElement(
        "#media-upload-selection"
    ),
    uploadSelectionCount: requireElement(
        "#media-upload-selection-count"
    ),
    uploadFileList: requireElement(
        "#media-upload-file-list"
    ),
    uploadClearButton: requireElement(
        "#media-upload-clear"
    ),
    uploadResult: requireElement(
        "#media-upload-result"
    ),
    uploadError: requireElement(
        "#media-upload-error"
    ),
};


/* UI helpers */

function announce(message) {
    if (!elements.announcement) {
        return;
    }

    elements.announcement.textContent = "";

    window.requestAnimationFrame(() => {
        elements.announcement.textContent = message;
    });
}

function setHidden(element, hidden) {
    if (!element) {
        return;
    }

    element.hidden = hidden;
}

function setLoading(loading) {
    state.loading = loading;

    setHidden(
        elements.loadingState,
        !loading
    );

    elements.refreshButton.disabled = loading;
    elements.refreshButton.textContent = (
        loading
            ? "Refreshing…"
            : "Refresh"
    );

    elements.retryButton.disabled = loading;

}

function showError(message) {
    setLoading(false);

    setHidden(
        elements.errorState,
        false
    );

    setHidden(
        elements.emptyState,
        true
    );

    setHidden(
        elements.items,
        true
    );


    elements.errorMessage.textContent = message;

    elements.resultSummary.textContent = (
        "Media unavailable"
    );
}

function hideError() {
    setHidden(
        elements.errorState,
        true
    );
}


/* Formatting */

function formatBytes(value) {
    const bytes = Number(value);

    if (
        !Number.isFinite(bytes)
        || bytes < 0
    ) {
        return "Unknown size";
    }

    if (bytes === 0) {
        return "0 B";
    }

    const units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ];

    const unitIndex = Math.min(
        Math.floor(
            Math.log(bytes)
            / Math.log(1024)
        ),
        units.length - 1
    );

    const amount = (
        bytes
        / (1024 ** unitIndex)
    );

    const fractionDigits = (
        unitIndex === 0
            ? 0
            : amount >= 10
                ? 1
                : 2
    );

    return (
        `${amount.toFixed(fractionDigits)} `
        + units[unitIndex]
    );
}

function parseDate(value) {
    const date = new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return null;
    }

    return date;
}

function formatDate(value) {
    const date = parseDate(value);

    if (!date) {
        return "Unknown date";
    }

    return new Intl.DateTimeFormat(
        undefined,
        {
            dateStyle: "medium",
            timeStyle: "short",
        }
    ).format(date);
}

function dateTimestamp(value) {
    const date = parseDate(value);

    return (
        date
            ? date.getTime()
            : 0
    );
}

function pluralize(
    count,
    singular,
    plural
) {
    return (
        count === 1
            ? singular
            : plural
    );
}


/* Classification */

function categoryLabel(category) {
    return (
        CATEGORY_LABELS[category]
        ?? "Media"
    );
}

function normalizedMediaFile(file) {
    if (
        !file
        || typeof file !== "object"
    ) {
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
    } = file;

    if (
        typeof category !== "string"
        || typeof name !== "string"
        || typeof mediaType !== "string"
        || typeof mimeType !== "string"
        || typeof url !== "string"
        || typeof downloadUrl !== "string"
    ) {
        return null;
    }

    if (
        !Object.hasOwn(
            CATEGORY_LABELS,
            category
        )
    ) {
        return null;
    }

    return {
        category,
        name,
        mediaType,
        mimeType,
        sizeBytes: (
            Number.isFinite(
                Number(sizeBytes)
            )
                ? Number(sizeBytes)
                : 0
        ),
        modifiedAt: (
            typeof modifiedAt === "string"
                ? modifiedAt
                : ""
        ),
        url,
        downloadUrl,
    };
}


/* State helpers */

function updateSummary() {
    const pictureCount = (
        state.counts.pictures ?? 0
    );

    const videoCount = (
        state.counts.videos ?? 0
    );

    const soundCount = (
        state.counts.sounds ?? 0
    );


    elements.totalCount.textContent = (
        String(state.totalCount)
    );

    elements.pictureCount.textContent = (
        String(pictureCount)
    );

    elements.videoCount.textContent = (
        String(videoCount)
    );

    elements.soundCount.textContent = (
        String(soundCount)
    );

    elements.totalSize.textContent = (
        formatBytes(
            state.totalSizeBytes
        )
    );

    elements.filterAllCount.textContent = (
        String(state.totalCount)
    );

    elements.filterPictureCount.textContent = (
        String(pictureCount)
    );

    elements.filterVideoCount.textContent = (
        String(videoCount)
    );

    elements.filterSoundCount.textContent = (
        String(soundCount)
    );
}

function filteredFiles() {
    const query = (
        state.search
            .trim()
            .toLocaleLowerCase()
    );

    const filtered = state.media.filter(
        (file) => {
            const categoryMatches = (
                state.category === "all"
                || file.category === state.category
            );

            const searchMatches = (
                query.length === 0
                || file.name
                    .toLocaleLowerCase()
                    .includes(query)
            );

            return (
                categoryMatches
                && searchMatches
            );
        }
    );

    return sortFiles(filtered);
}

function sortFiles(files) {
    const sorted = [...files];

    sorted.sort(
        (left, right) => {
            switch (state.sort) {
                case "oldest":
                    return (
                        dateTimestamp(
                            left.modifiedAt
                        )
                        - dateTimestamp(
                            right.modifiedAt
                        )
                    );

                case "name-ascending":
                    return left.name.localeCompare(
                        right.name,
                        undefined,
                        {
                            numeric: true,
                            sensitivity: "base",
                        }
                    );

                case "name-descending":
                    return right.name.localeCompare(
                        left.name,
                        undefined,
                        {
                            numeric: true,
                            sensitivity: "base",
                        }
                    );

                case "size-descending":
                    return (
                        right.sizeBytes
                        - left.sizeBytes
                    );

                case "size-ascending":
                    return (
                        left.sizeBytes
                        - right.sizeBytes
                    );

                case "newest":
                default:
                    return (
                        dateTimestamp(
                            right.modifiedAt
                        )
                        - dateTimestamp(
                            left.modifiedAt
                        )
                    );
            }
        }
    );

    return sorted;
}

function updateFilterButtons() {
    for (
        const button
        of elements.categoryFilters
    ) {
        const category = (
            button.dataset.mediaCategory
        );

        const active = (
            category === state.category
        );

        button.classList.toggle(
            "is-active",
            active
        );

        button.setAttribute(
            "aria-pressed",
            String(active)
        );
    }
}

function updateViewButtons() {
    const gridActive = (
        state.view === "grid"
    );

    elements.gridViewButton.classList.toggle(
        "is-active",
        gridActive
    );

    elements.gridViewButton.setAttribute(
        "aria-pressed",
        String(gridActive)
    );

    elements.listViewButton.classList.toggle(
        "is-active",
        !gridActive
    );

    elements.listViewButton.setAttribute(
        "aria-pressed",
        String(!gridActive)
    );

    elements.items.classList.toggle(
        "media-grid",
        gridActive
    );

    elements.items.classList.toggle(
        "media-list",
        !gridActive
    );
}

function updateResultSummary(
    visibleCount
) {
    if (!elements.resultSummary) {
        return;
    }

    const hasFilter = (
        state.category !== "all"
        || state.search.trim() !== ""
    );

    if (!hasFilter) {
        elements.resultSummary.textContent = (
            `${visibleCount} `
            + pluralize(
                visibleCount,
                "file",
                "files"
            )
        );

        return;
    }

    elements.resultSummary.textContent = (
        `${visibleCount} of `
        + `${state.totalCount} `
        + pluralize(
            state.totalCount,
            "file",
            "files"
        )
    );
}

function updateEmptyState(
    visibleCount
) {
    const hasAnyMedia = (
        state.totalCount > 0
    );

    const hasSearch = (
        state.search.trim() !== ""
    );

    const hasCategoryFilter = (
        state.category !== "all"
    );

    if (visibleCount > 0) {
        setHidden(
            elements.emptyState,
            true
        );

        setHidden(
            elements.items,
            false
        );

        return;
    }

    setHidden(
        elements.items,
        true
    );

    setHidden(
        elements.emptyState,
        false
    );

    if (
        hasAnyMedia
        && (
            hasSearch
            || hasCategoryFilter
        )
    ) {
        elements.emptyTitle.textContent = (
            "No matching media"
        );

        elements.emptyMessage.textContent = (
            "Try another search or choose "
            + "a different media category."
        );

        return;
    }

    elements.emptyTitle.textContent = (
        "No media yet"
    );

    elements.emptyMessage.textContent = (
        "Pictures, recordings, and sounds "
        + "created on this robot will appear here."
    );
}


/* Rendering */

function createMediaCard(file) {
    const fragment = (
        elements.cardTemplate.content
            .cloneNode(true)
    );

    const card = fragment.querySelector(
        ".media-card"
    );

    const previewButton = (
        fragment.querySelector(
            ".media-preview-button"
        )
    );

    const image = fragment.querySelector(
        ".media-thumbnail-image"
    );

    const video = fragment.querySelector(
        ".media-thumbnail-video"
    );

    const placeholder = (
        fragment.querySelector(
            ".media-thumbnail-placeholder"
        )
    );

    const placeholderIcon = (
        fragment.querySelector(
            ".media-placeholder-icon"
        )
    );

    const typeLabel = fragment.querySelector(
        ".media-type-label"
    );

    const playIndicator = (
        fragment.querySelector(
            ".media-play-indicator"
        )
    );

    const name = fragment.querySelector(
        ".media-card-name"
    );

    const date = fragment.querySelector(
        ".media-card-date"
    );

    const size = fragment.querySelector(
        ".media-card-size"
    );

    const downloadButton = (
        fragment.querySelector(
            ".media-download-button"
        )
    );

    const deleteButton = (
        fragment.querySelector(
            ".media-delete-button"
        )
    );

    if (card) {
        card.dataset.mediaCategory = (
            file.category
        );
    }

    if (name) {
        name.textContent = file.name;
        name.title = file.name;
    }

    if (date) {
        date.textContent = formatDate(
            file.modifiedAt
        );
    }

    if (size) {
        size.textContent = formatBytes(
            file.sizeBytes
        );
    }

    if (typeLabel) {
        typeLabel.textContent = (
            categoryLabel(file.category)
        );
    }

    if (previewButton) {
        previewButton.setAttribute(
            "aria-label",
            `Preview ${file.name}`
        );

        previewButton.addEventListener(
            "click",
            () => {
                openPreview(file);
            }
        );
    }

    if (downloadButton) {
        downloadButton.href = (
            file.downloadUrl
        );

        downloadButton.setAttribute(
            "aria-label",
            `Download ${file.name}`
        );
    }

    if (deleteButton) {
        deleteButton.setAttribute(
            "aria-label",
            `Delete ${file.name}`
        );

        deleteButton.addEventListener(
            "click",
            () => {
                openDeleteDialog(file);
            }
        );
    }

    configureThumbnail(
        file,
        {
            image,
            video,
            placeholder,
            placeholderIcon,
            playIndicator,
        }
    );

    return fragment;
}

function configureThumbnail(
    file,
    thumbnailElements
) {
    const {
        image,
        video,
        placeholder,
        placeholderIcon,
        playIndicator,
    } = thumbnailElements;

    setHidden(image, true);
    setHidden(video, true);
    setHidden(playIndicator, true);

    /*
     * Always display a placeholder until a real thumbnail
     * has successfully loaded.
     */
    const placeholderSymbol = (
        file.category === "pictures"
            ? "▧"
            : file.category === "videos"
                ? "▶"
                : "♪"
    );

    showThumbnailPlaceholder(
        placeholder,
        placeholderIcon,
        placeholderSymbol
    );

    if (
        file.category === "pictures"
        && image
    ) {
        image.alt = file.name;
        image.loading = "eager";
        image.decoding = "async";

        image.addEventListener(
            "load",
            () => {
                setHidden(image, false);
                setHidden(placeholder, true);
            },
            {
                once: true,
            }
        );

        image.addEventListener(
            "error",
            () => {
                image.removeAttribute("src");
                setHidden(image, true);

                showThumbnailPlaceholder(
                    placeholder,
                    placeholderIcon,
                    "▧"
                );
            },
            {
                once: true,
            }
        );

        image.src = file.url;

        return;
    }

    if (
        file.category === "videos"
        && video
    ) {
        setHidden(
            playIndicator,
            false
        );

        video.addEventListener(
            "loadedmetadata",
            () => {
                /*
                 * Seeking slightly into the recording gives the
                 * browser a better chance of producing a frame
                 * than displaying the first frame at time zero.
                 */
                if (
                    Number.isFinite(video.duration)
                    && video.duration > 0.1
                ) {
                    video.currentTime = Math.min(
                        0.1,
                        video.duration / 2
                    );
                }
            },
            {
                once: true,
            }
        );

        video.addEventListener(
            "seeked",
            () => {
                setHidden(video, false);
                setHidden(placeholder, true);
            },
            {
                once: true,
            }
        );

        video.addEventListener(
            "loadeddata",
            () => {
                /*
                 * Some browsers render a frame without firing
                 * seeked, particularly for very short videos.
                 */
                setHidden(video, false);
                setHidden(placeholder, true);
            },
            {
                once: true,
            }
        );

        video.addEventListener(
            "error",
            () => {
                video.removeAttribute("src");
                setHidden(video, true);

                showThumbnailPlaceholder(
                    placeholder,
                    placeholderIcon,
                    "▶"
                );
            },
            {
                once: true,
            }
        );

        video.src = file.url;
        video.load();

        return;
    }

    setHidden(
        playIndicator,
        false
    );
}

function showThumbnailPlaceholder(
    placeholder,
    icon,
    symbol
) {
    if (icon) {
        icon.textContent = symbol;
    }

    setHidden(
        placeholder,
        false
    );
}

function renderMedia() {
    hideError();

    const files = filteredFiles();

    elements.items.replaceChildren();

    const fragment = (
        document.createDocumentFragment()
    );

    for (const file of files) {
        fragment.append(
            createMediaCard(file)
        );
    }

    elements.items.append(fragment);

    updateFilterButtons();
    updateViewButtons();
    updateResultSummary(
        files.length
    );
    updateEmptyState(
        files.length
    );
}


/* Data helpers */

async function responseErrorMessage(
    response,
    fallback
) {
    const contentType = (
        response.headers.get(
            "content-type"
        )
        ?? ""
    );

    if (
        contentType.includes(
            "application/json"
        )
    ) {
        try {
            const payload = await response.json();

            if (
                payload
                && typeof payload.reason === "string"
            ) {
                return payload.reason;
            }

            if (
                payload
                && typeof payload.error === "string"
            ) {
                return payload.error;
            }
        } catch {
            return fallback;
        }
    }

    try {
        const text = (
            await response.text()
        ).trim();

        if (text) {
            return text;
        }
    } catch {
        return fallback;
    }

    return fallback;
}

function errorMessage(
    error,
    fallback
) {
    if (
        error instanceof Error
        && error.message
    ) {
        return error.message;
    }

    return fallback;
}

function normalizeCounts(value) {
    if (
        !value
        || typeof value !== "object"
    ) {
        return {
            pictures: 0,
            videos: 0,
            sounds: 0,
        };
    }

    return {
        pictures: safeCount(
            value.pictures
        ),
        videos: safeCount(
            value.videos
        ),
        sounds: safeCount(
            value.sounds
        ),
    };
}

function safeCount(value) {
    const number = Number(value);

    if (
        !Number.isFinite(number)
        || number < 0
    ) {
        return 0;
    }

    return Math.floor(number);
}

function filenameExtension(
    filename
) {
    const index = filename.lastIndexOf(".");

    if (
        index < 0
        || index === filename.length - 1
    ) {
        return "";
    }

    return filename
        .slice(index)
        .toLocaleLowerCase();
}

function validateUploadFile(
    file
) {
    const extension = filenameExtension(
        file.name
    );

    if (VIDEO_EXTENSIONS.has(extension)) {
        return "Videos cannot be uploaded.";
    }

    if (!UPLOAD_EXTENSIONS.has(extension)) {
        return (
            "This file is not a supported "
            + "picture or sound."
        );
    }

    if (file.size === 0) {
        return "The file is empty.";
    }

    if (
        file.size
        > MAX_UPLOAD_FILE_SIZE
    ) {
        return (
            "The file exceeds the 25 MB "
            + "upload limit."
        );
    }

    return null;
}


/* Dialogs */

function stopPreviewMedia() {
    elements.previewVideo.pause();
    elements.previewVideo.removeAttribute(
        "src"
    );
    elements.previewVideo.load();

    elements.previewAudio.pause();
    elements.previewAudio.removeAttribute(
        "src"
    );
    elements.previewAudio.load();


    elements.previewImage.removeAttribute(
        "src"
    );
    elements.previewImage.alt = "";

    setHidden(
        elements.previewImage,
        true
    );

    setHidden(
        elements.previewVideo,
        true
    );

    setHidden(
        elements.previewAudio,
        true
    );
}

function openPreview(file) {
    stopPreviewMedia();

    state.previewFile = file;

    elements.previewCategory.textContent = (
        categoryLabel(file.category)
    );

    elements.previewTitle.textContent = (
        file.name
    );

    elements.previewDate.textContent = (
        formatDate(
            file.modifiedAt
        )
    );

    elements.previewSize.textContent = (
        formatBytes(
            file.sizeBytes
        )
    );

    elements.previewDownload.href = (
        file.downloadUrl
    );

    elements.previewDownload.setAttribute(
        "aria-label",
        `Download ${file.name}`
    );

    switch (file.category) {
        case "pictures":
            elements.previewImage.src = (
                file.url
            );

            elements.previewImage.alt = (
                file.name
            );

            setHidden(
                elements.previewImage,
                false
            );
            break;

        case "videos":
            elements.previewVideo.src = (
                file.url
            );

            setHidden(
                elements.previewVideo,
                false
            );
            break;

        case "sounds":
            elements.previewAudio.src = (
                file.url
            );

            setHidden(
                elements.previewAudio,
                false
            );
            break;

        default:
            return;
    }

    if (
        typeof elements.previewDialog
            .showModal
        === "function"
    ) {
        elements.previewDialog.showModal();
    }
}

function closePreview() {
    if (elements.previewDialog.open) {
        elements.previewDialog.close();
    }

    stopPreviewMedia();
    state.previewFile = null;
}

function openDeleteDialog(file) {
    state.deleteFile = file;

    elements.deleteName.textContent = (
        file.name
    );

    elements.deleteError.textContent = "";
    elements.deleteError.hidden = true;

    elements.deleteConfirmButton.disabled = (
        false
    );

    elements.deleteConfirmButton.textContent = (
        "Delete File"
    );

    if (
        typeof elements.deleteDialog
            .showModal
        === "function"
    ) {
        elements.deleteDialog.showModal();
    }
}

function closeDeleteDialog() {
    if (elements.deleteDialog.open) {
        elements.deleteDialog.close();
    }

    state.deleteFile = null;

    elements.deleteError.textContent = "";
    elements.deleteError.hidden = true;
}

function openUploadDialog() {
    resetUploadDialog();

    if (
        typeof elements.uploadDialog
            .showModal
        === "function"
    ) {
        elements.uploadDialog.showModal();
    }
}

function closeUploadDialog() {
    if (
        state.uploading
        || !elements.uploadDialog
    ) {
        return;
    }

    if (elements.uploadDialog.open) {
        elements.uploadDialog.close();
    }

    resetUploadDialog();
}


/* Upload */

function selectedUploadFiles() {
    return Array.from(
        elements.uploadInput.files
    );
}

function setUploadError(
    message
) {
    if (!elements.uploadError) {
        return;
    }

    elements.uploadError.textContent = (
        message
    );

    elements.uploadError.hidden = !message;
}

function clearUploadResult() {
    elements.uploadResult.textContent = "";
    elements.uploadResult.hidden = true;

    setUploadError("");
}

function updateUploadSelection() {
    const files = selectedUploadFiles();

    clearUploadResult();

    if (
        !elements.uploadSelection
        || !elements.uploadFileList
    ) {
        return;
    }

    elements.uploadFileList.replaceChildren();

    if (files.length === 0) {
        elements.uploadSelection.hidden = true;

        elements.uploadConfirmButton.disabled = true;

        return;
    }

    elements.uploadSelection.hidden = false;

    elements.uploadSelectionCount.textContent = (
        `${files.length} `
        + pluralize(
            files.length,
            "file selected",
            "files selected"
        )
    );

    let hasInvalidFile = (
        files.length > MAX_UPLOAD_FILES
    );

    for (const file of files) {
        const error = validateUploadFile(file);

        if (error) {
            hasInvalidFile = true;
        }

        const item = document.createElement("li");

        item.className = (
            error
                ? "media-upload-file is-invalid"
                : "media-upload-file is-valid"
        );

        const details = document.createElement(
            "div"
        );

        const name = document.createElement(
            "strong"
        );

        name.textContent = file.name;

        const metadata = document.createElement(
            "span"
        );

        metadata.textContent = (
            error
                ? error
                : formatBytes(file.size)
        );

        details.append(
            name,
            metadata
        );

        const indicator = document.createElement(
            "span"
        );

        indicator.className = (
            "media-upload-file-status"
        );

        indicator.textContent = (
            error
                ? "×"
                : "✓"
        );

        item.append(
            details,
            indicator
        );

        elements.uploadFileList.append(item);
    }

    if (files.length > MAX_UPLOAD_FILES) {
        setUploadError(
            "Only 10 files can be uploaded at once."
        );
    }

    elements.uploadConfirmButton.disabled = (
        hasInvalidFile
        || state.uploading
    );
}

function resetUploadDialog() {
    state.uploading = false;

    elements.uploadForm.reset();

    elements.uploadConfirmButton.disabled = true;
    elements.uploadConfirmButton.textContent = (
        "Upload Files"
    );

    elements.uploadCancelButton.disabled = false;

    elements.uploadCloseButton.disabled = false;

    elements.uploadSelection.hidden = true;

    elements.uploadFileList.replaceChildren();

    clearUploadResult();
}

async function uploadMedia(
    event
) {
    event.preventDefault();

    if (state.uploading) {
        return;
    }

    const files = selectedUploadFiles();

    if (files.length === 0) {
        setUploadError(
            "Choose at least one file."
        );

        return;
    }

    if (files.length > MAX_UPLOAD_FILES) {
        setUploadError(
            "Only 10 files can be uploaded at once."
        );

        return;
    }

    for (const file of files) {
        const error = validateUploadFile(file);

        if (error) {
            setUploadError(
                `${file.name}: ${error}`
            );

            return;
        }
    }

    const formData = new FormData();

    for (const file of files) {
        formData.append(
            "files",
            file,
            file.name
        );
    }

    state.uploading = true;
    setUploadError("");

    elements.uploadConfirmButton.disabled = true;
    elements.uploadConfirmButton.textContent = (
        "Uploading…"
    );

    elements.uploadCancelButton.disabled = true;

    elements.uploadCloseButton.disabled = true;

    try {
        const response = await fetch(
            MEDIA_UPLOAD_API_URL,
            {
                method: "POST",
                headers: {
                    Accept: "application/json",
                },
                body: formData,
            }
        );

        const payload = await response.json();

        const uploaded = (
            Array.isArray(payload.uploaded)
                ? payload.uploaded
                : []
        );

        const failed = (
            Array.isArray(payload.failed)
                ? payload.failed
                : []
        );

        if (
            !response.ok
            && uploaded.length === 0
        ) {
            const failureMessage = (
                failed.length > 0
                    ? failed
                        .map(
                            (failure) => (
                                `${failure.name}: `
                                + failure.reason
                            )
                        )
                        .join(" ")
                    : (
                        payload.reason
                        || payload.error
                        || "The files could not be uploaded."
                    )
            );

            throw new Error(
                failureMessage
            );
        }

        const resultParts = [];

        if (uploaded.length > 0) {
            resultParts.push(
                `Uploaded ${uploaded.length} `
                + pluralize(
                    uploaded.length,
                    "file",
                    "files"
                )
                + "."
            );
        }

        if (failed.length > 0) {
            resultParts.push(
                `${failed.length} `
                + pluralize(
                    failed.length,
                    "file failed",
                    "files failed"
                )
                + "."
            );
        }

        elements.uploadResult.textContent = (
            resultParts.join(" ")
        );

        elements.uploadResult.hidden = false;

        announce(
            `Uploaded ${uploaded.length} `
            + pluralize(
                uploaded.length,
                "media file",
                "media files"
            )
            + "."
        );

        await loadMedia({
            announceResult: false,
        });

        if (failed.length === 0) {
            window.setTimeout(
                closeUploadDialog,
                500
            );
        } else {
            setUploadError(
                failed
                    .map(
                        (failure) => (
                            `${failure.name}: `
                            + failure.reason
                        )
                    )
                    .join(" ")
            );
        }
    } catch (error) {
        setUploadError(
            errorMessage(
                error,
                "The files could not be uploaded."
            )
        );
    } finally {
        state.uploading = false;

        elements.uploadConfirmButton.textContent =
            "Upload Files";

        elements.uploadConfirmButton.disabled =
            selectedUploadFiles().length === 0;

        elements.uploadCancelButton.disabled = false;


        elements.uploadCloseButton.disabled = false;
    }
}


/* Delete */

async function deleteSelectedFile() {
    const file = state.deleteFile;

    if (!file) {
        return;
    }

    elements.deleteConfirmButton.disabled = (
        true
    );

    elements.deleteConfirmButton.textContent = (
        "Deleting…"
    );

    elements.deleteError.hidden = true;
    elements.deleteError.textContent = "";

    try {
        const response = await fetch(
            file.url,
            {
                method: "DELETE",
                headers: {
                    Accept: "application/json",
                },
            }
        );

        if (!response.ok) {
            throw new Error(
                await responseErrorMessage(
                    response,
                    "The media file could not be deleted."
                )
            );
        }

        closeDeleteDialog();

        announce(
            `${file.name} was deleted.`
        );

        await loadMedia({
            announceResult: false,
        });
    } catch (error) {
        elements.deleteError.textContent = (
            errorMessage(
                error,
                "The media file could not be deleted."
            )
        );

        elements.deleteError.hidden = false;
    } finally {
        elements.deleteConfirmButton.disabled = (
            false
        );

        elements.deleteConfirmButton.textContent = (
            "Delete File"
        );
    }
}


/* API */

async function loadMedia({
    announceResult = true,
} = {}) {
    if (state.loading) {
        return;
    }

    hideError();
    setHidden(
        elements.emptyState,
        true
    );
    setHidden(
        elements.items,
        true
    );

    setLoading(true);

    elements.resultSummary.textContent = (
            "Loading media…"
    );

    try {
        const response = await fetch(
            MEDIA_API_URL,
            {
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            }
        );

        if (!response.ok) {
            throw new Error(
                await responseErrorMessage(
                    response,
                    "Launchpad could not load media."
                )
            );
        }

        const payload = await response.json();

        const files = (
            Array.isArray(payload.files)
                ? payload.files
                    .map(normalizedMediaFile)
                    .filter(
                        (file) => file !== null
                    )
                : []
        );

        state.media = files;
        state.counts = normalizeCounts(
            payload.counts
        );

        state.totalCount = (
            safeCount(
                payload.total_count
            )
        );

        state.totalSizeBytes = Math.max(
            0,
            Number(
                payload.total_size_bytes
            ) || 0
        );

        /*
         * Keep the visible totals consistent even if an older
         * API response omits summary values.
         */
        if (
            state.totalCount
            !== state.media.length
        ) {
            state.totalCount = (
                state.media.length
            );
        }

        const calculatedCounts = {
            pictures: 0,
            videos: 0,
            sounds: 0,
        };

        let calculatedSize = 0;

        for (const file of state.media) {
            calculatedCounts[
                file.category
            ] += 1;

            calculatedSize += (
                file.sizeBytes
            );
        }

        state.counts = calculatedCounts;
        state.totalSizeBytes = (
            calculatedSize
        );

        updateSummary();
        renderMedia();

        if (announceResult) {
            announce(
                `Loaded ${state.totalCount} `
                + pluralize(
                    state.totalCount,
                    "media file",
                    "media files"
                )
                + "."
            );
        }
    } catch (error) {
        showError(
            errorMessage(
                error,
                "Launchpad could not load media."
            )
        );
    } finally {
        setLoading(false);
    }
}


/* UI */

function setCategory(category) {
    if (
        category !== "all"
        && !Object.hasOwn(
            CATEGORY_LABELS,
            category
        )
    ) {
        return;
    }

    state.category = category;
    renderMedia();

    announce(
        category === "all"
            ? "Showing all media."
            : `Showing ${category}.`
    );
}

function setView(view) {
    if (
        view !== "grid"
        && view !== "list"
    ) {
        return;
    }

    state.view = view;
    updateViewButtons();

    try {
        window.localStorage.setItem(
            "betabox-media-view",
            view
        );
    } catch {
        // Local storage is optional.
    }

    announce(
        view === "grid"
            ? "Grid view enabled."
            : "List view enabled."
    );
}

function restoreViewPreference() {
    try {
        const storedView = (
            window.localStorage.getItem(
                "betabox-media-view"
            )
        );

        if (
            storedView === "grid"
            || storedView === "list"
        ) {
            state.view = storedView;
        }
    } catch {
        // Local storage is optional.
    }
}


/* Initialization */

function initializeMediaPage() {
    restoreViewPreference();
    setupEventListeners();
    updateViewButtons();

    void loadMedia();
}


/* Event listeners */

function setupEventListeners() {
    elements.refreshButton.addEventListener(
        "click",
        () => {
            void loadMedia();
        }
    );

    elements.retryButton.addEventListener(
        "click",
        () => {
            void loadMedia();
        }
    );

    for (
        const button
        of elements.categoryFilters
    ) {
        button.addEventListener(
            "click",
            () => {
                setCategory(
                    button.dataset.mediaCategory
                    ?? "all"
                );
            }
        );
    }

    elements.searchInput.addEventListener(
        "input",
        (event) => {
            state.search = (
                event.currentTarget.value
            );

            renderMedia();
        }
    );

    elements.sortSelect.addEventListener(
        "change",
        (event) => {
            state.sort = (
                event.currentTarget.value
            );

            renderMedia();
        }
    );

    elements.gridViewButton.addEventListener(
        "click",
        () => {
            setView("grid");
        }
    );

    elements.listViewButton.addEventListener(
        "click",
        () => {
            setView("list");
        }
    );

    elements.previewCloseButton.addEventListener(
        "click",
        closePreview
    );

    elements.previewDialog.addEventListener(
        "close",
        () => {
            stopPreviewMedia();
            state.previewFile = null;
        }
    );

    elements.previewDialog.addEventListener(
        "click",
        (event) => {
            if (
                event.target
                === elements.previewDialog
            ) {
                closePreview();
            }
        }
    );

    elements.deleteDialog.addEventListener(
        "close",
        () => {
            state.deleteFile = null;

            elements.deleteError.textContent = "";
            elements.deleteError.hidden = true;
        }
    );

    elements.deleteDialog.addEventListener(
        "click",
        (event) => {
            if (
                event.target
                === elements.deleteDialog
            ) {
                closeDeleteDialog();
            }
        }
    );

    elements.deleteConfirmButton.addEventListener(
        "click",
        deleteSelectedFile
    );

    elements.uploadOpenButton.addEventListener(
        "click",
        openUploadDialog
    );

    elements.uploadCloseButton.addEventListener(
        "click",
        closeUploadDialog
    );

    elements.uploadCancelButton.addEventListener(
        "click",
        closeUploadDialog
    );

    elements.uploadInput.addEventListener(
        "change",
        updateUploadSelection
    );

    elements.uploadClearButton.addEventListener(
        "click",
        () => {
            elements.uploadInput.value = "";

            updateUploadSelection();
        }
    );

    elements.uploadForm.addEventListener(
        "submit",
        (event) => {
            void uploadMedia(event);
        }
    );

    elements.uploadDialog.addEventListener(
        "cancel",
        (event) => {
            if (state.uploading) {
                event.preventDefault();
                return;
            }

            resetUploadDialog();
        }
    );

    elements.uploadDialog.addEventListener(
        "close",
        resetUploadDialog
    );

    elements.uploadDialog.addEventListener(
        "click",
        (event) => {
            if (
                event.target
                === elements.uploadDialog
            ) {
                closeUploadDialog();
            }
        }
    );
}

initializeMediaPage();
