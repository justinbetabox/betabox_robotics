"use strict";

import {
    MAX_UPLOAD_FILES,
    MAX_UPLOAD_FILE_SIZE,
    MEDIA_UPLOAD_API_URL,
    UPLOAD_EXTENSIONS,
    VIDEO_EXTENSIONS,
} from "./constants.js";

import { elements } from "./dom.js";

import {
    errorMessage,
    filenameExtension,
    formatBytes,
    pluralize,
} from "./helpers.js";

import { state } from "./state.js";

import { announce } from "./utils.js";

function selectedUploadFiles() {
    return Array.from(elements.uploadInput.files);
}

function setUploadError(message) {
    elements.uploadError.textContent = message;

    elements.uploadError.hidden = message === "";
}

function clearUploadResult() {
    elements.uploadResult.textContent = "";

    elements.uploadResult.hidden = true;

    setUploadError("");
}

function validateUploadFile(file) {
    const extension = filenameExtension(file.name);

    if (VIDEO_EXTENSIONS.has(extension)) {
        return "Videos cannot be uploaded.";
    }

    if (!UPLOAD_EXTENSIONS.has(extension)) {
        return "This file is not a supported " + "picture or sound.";
    }

    if (file.size === 0) {
        return "The file is empty.";
    }

    if (file.size > MAX_UPLOAD_FILE_SIZE) {
        return "The file exceeds the 25 MB " + "upload limit.";
    }

    return null;
}

function createUploadFileItem(file) {
    const validationError = validateUploadFile(file);

    const item = document.createElement("li");

    item.className =
        validationError === null
            ? "media-upload-file is-valid"
            : "media-upload-file is-invalid";

    const details = document.createElement("div");

    const name = document.createElement("strong");

    name.textContent = file.name;

    const metadata = document.createElement("span");

    metadata.textContent = validationError ?? formatBytes(file.size);

    details.append(name, metadata);

    const indicator = document.createElement("span");

    indicator.className = "media-upload-file-status";

    indicator.textContent = validationError === null ? "✓" : "×";

    indicator.setAttribute("aria-hidden", "true");

    item.append(details, indicator);

    return {
        element: item,
        valid: validationError === null,
    };
}

export function updateUploadSelection({ clearResult = true } = {}) {
    const files = selectedUploadFiles();

    if (clearResult) {
        clearUploadResult();
    }

    elements.uploadFileList.replaceChildren();

    if (files.length === 0) {
        elements.uploadSelection.hidden = true;

        elements.uploadConfirmButton.disabled = true;

        return;
    }

    elements.uploadSelection.hidden = false;

    elements.uploadSelectionCount.textContent =
        `${files.length} ` +
        pluralize(files.length, "file selected", "files selected");

    let hasInvalidFile = files.length > MAX_UPLOAD_FILES;

    for (const file of files) {
        const result = createUploadFileItem(file);

        if (!result.valid) {
            hasInvalidFile = true;
        }

        elements.uploadFileList.append(result.element);
    }

    if (files.length > MAX_UPLOAD_FILES) {
        setUploadError("Only 10 files can be uploaded at once.");
    }

    elements.uploadConfirmButton.disabled = hasInvalidFile || state.uploading;
}

export function resetUploadDialog() {
    state.uploading = false;

    elements.uploadForm.reset();

    elements.uploadConfirmButton.disabled = true;

    elements.uploadConfirmButton.textContent = "Upload Files";

    elements.uploadCancelButton.disabled = false;

    elements.uploadCloseButton.disabled = false;

    elements.uploadSelection.hidden = true;

    elements.uploadFileList.replaceChildren();

    clearUploadResult();
}

export function openUploadDialog() {
    resetUploadDialog();

    elements.uploadDialog.showModal();
}

export function closeUploadDialog() {
    if (state.uploading) {
        return;
    }

    if (elements.uploadDialog.open) {
        elements.uploadDialog.close();
    }

    resetUploadDialog();
}

function validateUploadSelection(files) {
    if (files.length === 0) {
        return "Choose at least one file.";
    }

    if (files.length > MAX_UPLOAD_FILES) {
        return "Only 10 files can be uploaded at once.";
    }

    for (const file of files) {
        const validationError = validateUploadFile(file);

        if (validationError !== null) {
            return `${file.name}: ` + validationError;
        }
    }

    return null;
}

function normalizeUploadPayload(payload) {
    if (
        payload === null ||
        typeof payload !== "object" ||
        Array.isArray(payload)
    ) {
        throw new Error("The upload service returned an invalid response.");
    }

    return {
        uploaded: Array.isArray(payload.uploaded) ? payload.uploaded : [],

        failed: Array.isArray(payload.failed) ? payload.failed : [],

        reason: typeof payload.reason === "string" ? payload.reason : "",

        error: typeof payload.error === "string" ? payload.error : "",
    };
}

function uploadFailureMessage(payload) {
    if (payload.failed.length > 0) {
        return payload.failed
            .map((failure) => {
                const name =
                    typeof failure?.name === "string" ? failure.name : "File";

                const reason =
                    typeof failure?.reason === "string"
                        ? failure.reason
                        : "Upload failed.";

                return `${name}: ${reason}`;
            })
            .join(" ");
    }

    return (
        payload.reason || payload.error || "The files could not be uploaded."
    );
}

export async function uploadMedia(event, { reloadMedia } = {}) {
    event.preventDefault();

    if (state.uploading) {
        return;
    }

    const files = selectedUploadFiles();

    const validationError = validateUploadSelection(files);

    if (validationError !== null) {
        setUploadError(validationError);

        return;
    }

    const formData = new FormData();

    for (const file of files) {
        formData.append("files", file, file.name);
    }

    state.uploading = true;

    setUploadError("");

    elements.uploadConfirmButton.disabled = true;

    elements.uploadConfirmButton.textContent = "Uploading…";

    elements.uploadCancelButton.disabled = true;

    elements.uploadCloseButton.disabled = true;

    try {
        const response = await fetch(MEDIA_UPLOAD_API_URL, {
            method: "POST",
            headers: {
                Accept: "application/json",
            },
            body: formData,
        });

        const payload = normalizeUploadPayload(await response.json());

        if (!response.ok && payload.uploaded.length === 0) {
            throw new Error(uploadFailureMessage(payload));
        }

        const resultParts = [];

        if (payload.uploaded.length > 0) {
            resultParts.push(
                `Uploaded ${payload.uploaded.length} ` +
                    pluralize(payload.uploaded.length, "file", "files") +
                    ".",
            );
        }

        if (payload.failed.length > 0) {
            resultParts.push(
                `${payload.failed.length} ` +
                    pluralize(
                        payload.failed.length,
                        "file failed",
                        "files failed",
                    ) +
                    ".",
            );
        }

        elements.uploadResult.textContent = resultParts.join(" ");

        elements.uploadResult.hidden = false;

        announce(
            `Uploaded ${payload.uploaded.length} ` +
                pluralize(
                    payload.uploaded.length,
                    "media file",
                    "media files",
                ) +
                ".",
        );

        if (typeof reloadMedia === "function") {
            await reloadMedia({
                announceResult: false,
            });
        }

        if (payload.failed.length === 0) {
            window.setTimeout(closeUploadDialog, 500);
        } else {
            setUploadError(uploadFailureMessage(payload));
        }
    } catch (error) {
        setUploadError(errorMessage(error, "The files could not be uploaded."));
    } finally {
        state.uploading = false;

        elements.uploadConfirmButton.textContent = "Upload Files";

        updateUploadSelection();

        elements.uploadCancelButton.disabled = false;

        elements.uploadCloseButton.disabled = false;
    }
}
