"use strict";

import {
    CAMERA_OFFSET_MAX,
    CAMERA_OFFSET_MIN,
    CAMERA_OFFSET_STEP,
} from "./constants.js";

import { elements } from "./dom.js";

import {
    clamp,
    formatOffset,
    setBadge,
    showTemporaryMessage,
} from "./helpers.js";

import { requestJson } from "./api.js";

import { state } from "./state.js";

/* Rendering */

export function renderCameraMount(cameraMount) {
    const panOffset = Number(cameraMount.pan_offset);

    const tiltOffset = Number(cameraMount.tilt_offset);

    const validPanOffset = Number.isFinite(panOffset) ? panOffset : 0;

    const validTiltOffset = Number.isFinite(tiltOffset) ? tiltOffset : 0;

    state.camera.savedPanOffset = validPanOffset;

    state.camera.savedTiltOffset = validTiltOffset;

    state.camera.panOffset = validPanOffset;

    state.camera.tiltOffset = validTiltOffset;

    renderCameraMountEditor();

    const adjusted = validPanOffset !== 0 || validTiltOffset !== 0;

    setBadge(
        elements.camera.status,
        adjusted ? "Adjusted" : "Default",
        adjusted ? "healthy" : "neutral",
    );
}

export function renderCameraMountEditor() {
    elements.camera.panOffset.textContent = formatOffset(
        state.camera.panOffset,
    );

    elements.camera.tiltOffset.textContent = formatOffset(
        state.camera.tiltOffset,
    );

    const changed =
        state.camera.panOffset !== state.camera.savedPanOffset ||
        state.camera.tiltOffset !== state.camera.savedTiltOffset;

    elements.camera.saveButton.disabled = !changed;

    elements.camera.resetButton.disabled = !changed;

    elements.camera.message.textContent = changed
        ? "Unsaved camera mount changes."
        : "";
}

/* Preview */

async function previewCameraMount() {
    await requestJson("/api/calibration/camera-mount/preview", {
        method: "POST",
        body: {
            pan_offset: state.camera.panOffset,
            tilt_offset: state.camera.tiltOffset,
        },
        invalidMessage: "Camera mount API returned " + "an invalid response.",
        errorMessage: "Unable to move camera.",
    });
}

function scheduleCameraPreview() {
    if (state.camera.previewTimer !== null) {
        window.clearTimeout(state.camera.previewTimer);
    }

    state.camera.previewTimer = window.setTimeout(async () => {
        state.camera.previewTimer = null;

        setCameraControlsDisabled(true);

        try {
            await previewCameraMount();
        } catch (error) {
            elements.camera.message.textContent =
                error instanceof Error
                    ? error.message
                    : "Unable to move " + "camera.";
        } finally {
            setCameraControlsDisabled(false);

            renderCameraMountEditor();
        }
    }, 75);
}

/* Persistence */

async function saveCameraMount(renderCalibration) {
    elements.camera.saveButton.disabled = true;

    elements.camera.resetButton.disabled = true;

    elements.refreshButton.disabled = true;

    elements.camera.message.textContent = "Saving…";

    try {
        const payload = await requestJson("/api/calibration/camera-mount", {
            method: "PUT",
            body: {
                pan_offset: state.camera.panOffset,
                tilt_offset: state.camera.tiltOffset,
            },
            errorMessage: "Unable to save camera mount " + "calibration.",
        });

        renderCalibration(payload);

        showTemporaryMessage(
            elements.camera.message,
            "Camera mount calibration saved.",
            () =>
                state.camera.panOffset === state.camera.savedPanOffset &&
                state.camera.tiltOffset === state.camera.savedTiltOffset,
        );

        elements.announcement.textContent = "Camera mount calibration saved.";
    } catch (error) {
        renderCameraMountEditor();

        elements.camera.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to save camera mount " + "calibration.";
    } finally {
        elements.refreshButton.disabled = false;
    }
}

/* Cleanup */

export function restoreSavedCameraMount() {
    if (state.camera.previewTimer !== null) {
        window.clearTimeout(state.camera.previewTimer);

        state.camera.previewTimer = null;
    }

    if (
        state.camera.panOffset === state.camera.savedPanOffset &&
        state.camera.tiltOffset === state.camera.savedTiltOffset
    ) {
        return;
    }

    fetch("/api/calibration/camera-mount/preview", {
        method: "POST",
        keepalive: true,
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            pan_offset: state.camera.savedPanOffset,
            tilt_offset: state.camera.savedTiltOffset,
        }),
    }).catch(() => {
        /*
         * The page is leaving, so there is
         * nowhere useful to display an error.
         */
    });
}

/* Controls */

export function setCameraControlsDisabled(disabled) {
    elements.camera.panIncreaseButton.disabled = disabled;

    elements.camera.panDecreaseButton.disabled = disabled;

    elements.camera.tiltIncreaseButton.disabled = disabled;

    elements.camera.tiltDecreaseButton.disabled = disabled;

    if (disabled) {
        elements.camera.saveButton.disabled = true;

        elements.camera.resetButton.disabled = true;
    }
}

/* Setup */

export function setupCameraMount({ renderCalibration }) {
    if (typeof renderCalibration !== "function") {
        throw new TypeError("renderCalibration must be a function");
    }

    elements.camera.panIncreaseButton.addEventListener("click", () => {
        state.camera.panOffset = clamp(
            state.camera.panOffset + CAMERA_OFFSET_STEP,
            CAMERA_OFFSET_MIN,
            CAMERA_OFFSET_MAX,
        );

        renderCameraMountEditor();
        scheduleCameraPreview();
    });

    elements.camera.panDecreaseButton.addEventListener("click", () => {
        state.camera.panOffset = clamp(
            state.camera.panOffset - CAMERA_OFFSET_STEP,
            CAMERA_OFFSET_MIN,
            CAMERA_OFFSET_MAX,
        );

        renderCameraMountEditor();
        scheduleCameraPreview();
    });

    elements.camera.tiltIncreaseButton.addEventListener("click", () => {
        state.camera.tiltOffset = clamp(
            state.camera.tiltOffset + CAMERA_OFFSET_STEP,
            CAMERA_OFFSET_MIN,
            CAMERA_OFFSET_MAX,
        );

        renderCameraMountEditor();
        scheduleCameraPreview();
    });

    elements.camera.tiltDecreaseButton.addEventListener("click", () => {
        state.camera.tiltOffset = clamp(
            state.camera.tiltOffset - CAMERA_OFFSET_STEP,
            CAMERA_OFFSET_MIN,
            CAMERA_OFFSET_MAX,
        );

        renderCameraMountEditor();
        scheduleCameraPreview();
    });

    elements.camera.resetButton.addEventListener("click", () => {
        state.camera.panOffset = state.camera.savedPanOffset;

        state.camera.tiltOffset = state.camera.savedTiltOffset;

        renderCameraMountEditor();
        scheduleCameraPreview();
    });

    elements.camera.saveButton.addEventListener("click", () => {
        void saveCameraMount(renderCalibration);
    });
}
