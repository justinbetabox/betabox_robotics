const MEDIA_API_URL = "/api/media";

const CATEGORY_LABELS = {
    pictures: "Picture",
    videos: "Video",
    sounds: "Sound",
};

const state = {
    files: [],
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
};


const elements = {
    refreshButton: document.querySelector(
        "#media-refresh"
    ),
    retryButton: document.querySelector(
        "#media-retry"
    ),

    totalCount: document.querySelector(
        "#media-total-count"
    ),
    pictureCount: document.querySelector(
        "#media-picture-count"
    ),
    videoCount: document.querySelector(
        "#media-video-count"
    ),
    soundCount: document.querySelector(
        "#media-sound-count"
    ),
    totalSize: document.querySelector(
        "#media-total-size"
    ),

    filterAllCount: document.querySelector(
        "#media-filter-all-count"
    ),
    filterPictureCount: document.querySelector(
        "#media-filter-picture-count"
    ),
    filterVideoCount: document.querySelector(
        "#media-filter-video-count"
    ),
    filterSoundCount: document.querySelector(
        "#media-filter-sound-count"
    ),

    resultSummary: document.querySelector(
        "#media-result-summary"
    ),
    categoryFilters: Array.from(
        document.querySelectorAll(
            "[data-media-category]"
        )
    ),
    searchInput: document.querySelector(
        "#media-search"
    ),
    sortSelect: document.querySelector(
        "#media-sort"
    ),

    gridViewButton: document.querySelector(
        "#media-grid-view"
    ),
    listViewButton: document.querySelector(
        "#media-list-view"
    ),

    loadingState: document.querySelector(
        "#media-loading"
    ),
    errorState: document.querySelector(
        "#media-error"
    ),
    errorMessage: document.querySelector(
        "#media-error-message"
    ),
    emptyState: document.querySelector(
        "#media-empty"
    ),
    emptyTitle: document.querySelector(
        "#media-empty-title"
    ),
    emptyMessage: document.querySelector(
        "#media-empty-message"
    ),
    items: document.querySelector(
        "#media-items"
    ),
    cardTemplate: document.querySelector(
        "#media-card-template"
    ),
    announcement: document.querySelector(
        "#media-announcement"
    ),

    previewDialog: document.querySelector(
        "#media-preview-dialog"
    ),
    previewCloseButton: document.querySelector(
        "#media-preview-close"
    ),
    previewCategory: document.querySelector(
        "#media-preview-category"
    ),
    previewTitle: document.querySelector(
        "#media-preview-title"
    ),
    previewImage: document.querySelector(
        "#media-preview-image"
    ),
    previewVideo: document.querySelector(
        "#media-preview-video"
    ),
    previewAudio: document.querySelector(
        "#media-preview-audio"
    ),
    previewDate: document.querySelector(
        "#media-preview-date"
    ),
    previewSize: document.querySelector(
        "#media-preview-size"
    ),
    previewDownload: document.querySelector(
        "#media-preview-download"
    ),

    deleteDialog: document.querySelector(
        "#media-delete-dialog"
    ),
    deleteName: document.querySelector(
        "#media-delete-name"
    ),
    deleteError: document.querySelector(
        "#media-delete-error"
    ),
    deleteConfirmButton: document.querySelector(
        "#media-delete-confirm"
    ),
};


function assertRequiredElements() {
    const requiredElements = {
        items: elements.items,
        cardTemplate: elements.cardTemplate,
        loadingState: elements.loadingState,
        errorState: elements.errorState,
        emptyState: elements.emptyState,
        previewDialog: elements.previewDialog,
        deleteDialog: elements.deleteDialog,
    };

    for (
        const [name, element]
        of Object.entries(requiredElements)
    ) {
        if (!element) {
            throw new Error(
                `Media page element is missing: ${name}`
            );
        }
    }
}


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

    if (elements.refreshButton) {
        elements.refreshButton.disabled = loading;
        elements.refreshButton.textContent = (
            loading
                ? "Refreshing…"
                : "Refresh"
        );
    }

    if (elements.retryButton) {
        elements.retryButton.disabled = loading;
    }
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

    if (elements.errorMessage) {
        elements.errorMessage.textContent = message;
    }

    if (elements.resultSummary) {
        elements.resultSummary.textContent = (
            "Media unavailable"
        );
    }
}


function hideError() {
    setHidden(
        elements.errorState,
        true
    );
}


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

    if (elements.totalCount) {
        elements.totalCount.textContent = (
            String(state.totalCount)
        );
    }

    if (elements.pictureCount) {
        elements.pictureCount.textContent = (
            String(pictureCount)
        );
    }

    if (elements.videoCount) {
        elements.videoCount.textContent = (
            String(videoCount)
        );
    }

    if (elements.soundCount) {
        elements.soundCount.textContent = (
            String(soundCount)
        );
    }

    if (elements.totalSize) {
        elements.totalSize.textContent = (
            formatBytes(
                state.totalSizeBytes
            )
        );
    }

    if (elements.filterAllCount) {
        elements.filterAllCount.textContent = (
            String(state.totalCount)
        );
    }

    if (elements.filterPictureCount) {
        elements.filterPictureCount.textContent = (
            String(pictureCount)
        );
    }

    if (elements.filterVideoCount) {
        elements.filterVideoCount.textContent = (
            String(videoCount)
        );
    }

    if (elements.filterSoundCount) {
        elements.filterSoundCount.textContent = (
            String(soundCount)
        );
    }
}


function filteredFiles() {
    const query = (
        state.search
            .trim()
            .toLocaleLowerCase()
    );

    const filtered = state.files.filter(
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


function dateTimestamp(value) {
    const date = parseDate(value);

    return (
        date
            ? date.getTime()
            : 0
    );
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

    if (elements.gridViewButton) {
        elements.gridViewButton.classList.toggle(
            "is-active",
            gridActive
        );

        elements.gridViewButton.setAttribute(
            "aria-pressed",
            String(gridActive)
        );
    }

    if (elements.listViewButton) {
        elements.listViewButton.classList.toggle(
            "is-active",
            !gridActive
        );

        elements.listViewButton.setAttribute(
            "aria-pressed",
            String(!gridActive)
        );
    }

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
        if (elements.emptyTitle) {
            elements.emptyTitle.textContent = (
                "No matching media"
            );
        }

        if (elements.emptyMessage) {
            elements.emptyMessage.textContent = (
                "Try another search or choose "
                + "a different media category."
            );
        }

        return;
    }

    if (elements.emptyTitle) {
        elements.emptyTitle.textContent = (
            "No media yet"
        );
    }

    if (elements.emptyMessage) {
        elements.emptyMessage.textContent = (
            "Pictures, recordings, and sounds "
            + "created on this robot will appear here."
        );
    }
}


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


function stopPreviewMedia() {
    if (elements.previewVideo) {
        elements.previewVideo.pause();
        elements.previewVideo.removeAttribute(
            "src"
        );
        elements.previewVideo.load();
    }

    if (elements.previewAudio) {
        elements.previewAudio.pause();
        elements.previewAudio.removeAttribute(
            "src"
        );
        elements.previewAudio.load();
    }

    if (elements.previewImage) {
        elements.previewImage.removeAttribute(
            "src"
        );
        elements.previewImage.alt = "";
    }

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

    if (elements.previewCategory) {
        elements.previewCategory.textContent = (
            categoryLabel(file.category)
        );
    }

    if (elements.previewTitle) {
        elements.previewTitle.textContent = (
            file.name
        );
    }

    if (elements.previewDate) {
        elements.previewDate.textContent = (
            formatDate(
                file.modifiedAt
            )
        );
    }

    if (elements.previewSize) {
        elements.previewSize.textContent = (
            formatBytes(
                file.sizeBytes
            )
        );
    }

    if (elements.previewDownload) {
        elements.previewDownload.href = (
            file.downloadUrl
        );

        elements.previewDownload.setAttribute(
            "aria-label",
            `Download ${file.name}`
        );
    }

    switch (file.category) {
        case "pictures":
            if (elements.previewImage) {
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
            }
            break;

        case "videos":
            if (elements.previewVideo) {
                elements.previewVideo.src = (
                    file.url
                );

                setHidden(
                    elements.previewVideo,
                    false
                );
            }
            break;

        case "sounds":
            if (elements.previewAudio) {
                elements.previewAudio.src = (
                    file.url
                );

                setHidden(
                    elements.previewAudio,
                    false
                );
            }
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

    if (elements.deleteName) {
        elements.deleteName.textContent = (
            file.name
        );
    }

    if (elements.deleteError) {
        elements.deleteError.textContent = "";
        elements.deleteError.hidden = true;
    }

    if (elements.deleteConfirmButton) {
        elements.deleteConfirmButton.disabled = (
            false
        );

        elements.deleteConfirmButton.textContent = (
            "Delete File"
        );
    }

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

    if (elements.deleteError) {
        elements.deleteError.textContent = "";
        elements.deleteError.hidden = true;
    }
}


async function deleteSelectedFile() {
    const file = state.deleteFile;

    if (!file) {
        return;
    }

    if (elements.deleteConfirmButton) {
        elements.deleteConfirmButton.disabled = (
            true
        );

        elements.deleteConfirmButton.textContent = (
            "Deleting…"
        );
    }

    if (elements.deleteError) {
        elements.deleteError.hidden = true;
        elements.deleteError.textContent = "";
    }

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
        if (elements.deleteError) {
            elements.deleteError.textContent = (
                errorMessage(
                    error,
                    "The media file could not be deleted."
                )
            );

            elements.deleteError.hidden = false;
        }
    } finally {
        if (elements.deleteConfirmButton) {
            elements.deleteConfirmButton.disabled = (
                false
            );

            elements.deleteConfirmButton.textContent = (
                "Delete File"
            );
        }
    }
}


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

    if (elements.resultSummary) {
        elements.resultSummary.textContent = (
            "Loading media…"
        );
    }

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

        state.files = files;
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
            !== state.files.length
        ) {
            state.totalCount = (
                state.files.length
            );
        }

        const calculatedCounts = {
            pictures: 0,
            videos: 0,
            sounds: 0,
        };

        let calculatedSize = 0;

        for (const file of state.files) {
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


function bindEvents() {
    elements.refreshButton?.addEventListener(
        "click",
        () => {
            loadMedia();
        }
    );

    elements.retryButton?.addEventListener(
        "click",
        () => {
            loadMedia();
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

    elements.searchInput?.addEventListener(
        "input",
        (event) => {
            state.search = (
                event.currentTarget.value
            );

            renderMedia();
        }
    );

    elements.sortSelect?.addEventListener(
        "change",
        (event) => {
            state.sort = (
                event.currentTarget.value
            );

            renderMedia();
        }
    );

    elements.gridViewButton?.addEventListener(
        "click",
        () => {
            setView("grid");
        }
    );

    elements.listViewButton?.addEventListener(
        "click",
        () => {
            setView("list");
        }
    );

    elements.previewCloseButton?.addEventListener(
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

            if (elements.deleteError) {
                elements.deleteError.textContent = "";
                elements.deleteError.hidden = true;
            }
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

    elements.deleteConfirmButton?.addEventListener(
        "click",
        deleteSelectedFile
    );
}


function initialize() {
    assertRequiredElements();
    restoreViewPreference();
    bindEvents();
    updateViewButtons();

    loadMedia();
}


initialize();
