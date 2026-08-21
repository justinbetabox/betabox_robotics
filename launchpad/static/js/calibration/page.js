"use strict";

import { elements } from "./dom.js";

import { setBadge } from "./helpers.js";

import { requestJson } from "./api.js";

import { state } from "./state.js";

import {
    renderSteering,
    renderSteeringEditor,
    setSteeringControlsDisabled,
    setupSteering,
} from "./steering.js";

import {
    renderCameraMount,
    renderCameraMountEditor,
    setCameraControlsDisabled,
    setupCameraMount,
} from "./camera_mount.js";

import {
    renderMotorEditor,
    renderMotors,
    setMotorControlsDisabled,
    setupMotors,
} from "./motors.js";

import {
    renderGrayscale,
    renderGrayscaleEditor,
    setGrayscaleControlsDisabled,
    setupGrayscale,
} from "./grayscale.js";

/* Connection state */

function setConnectionState(status, message) {
    elements.connectionStatus.className = `connection-status status-${status}`;

    elements.connectionStatus.textContent = message;
}

/* Page state */

function showLoading() {
    elements.loadingPanel.hidden = state.hasLoadedOnce;

    elements.contentPanel.hidden = !state.hasLoadedOnce;

    elements.errorPanel.hidden = true;

    elements.refreshButton.disabled = true;

    elements.resetDefaultsButton.disabled = true;

    elements.refreshButton.textContent = "Refreshing…";

    setSteeringControlsDisabled(true);
    setCameraControlsDisabled(true);
    setMotorControlsDisabled(true);
    setGrayscaleControlsDisabled(true);

    setConnectionState("connecting", "Updating…");

    elements.updatedTime.textContent = state.hasLoadedOnce
        ? "Refreshing calibration…"
        : "Loading calibration…";
}

function showError(message) {
    elements.loadingPanel.hidden = true;

    elements.contentPanel.hidden = true;

    elements.errorPanel.hidden = false;

    elements.refreshButton.disabled = false;

    elements.resetDefaultsButton.disabled = false;

    elements.refreshButton.textContent = "Refresh";

    elements.errorMessage.textContent = message;

    setConnectionState("error", "Unavailable");

    elements.announcement.textContent = "Calibration could not be loaded.";
}

/* Metadata */

function renderMetadata(payload) {
    const saved = Boolean(payload.saved);

    setBadge(
        elements.sourceBadge,
        saved ? "Saved" : "Defaults",
        saved ? "healthy" : "neutral",
    );

    const now = new Date();

    elements.updatedTime.textContent = `Last updated ${now.toLocaleTimeString(
        [],
        {
            hour: "numeric",
            minute: "2-digit",
        },
    )}`;
}

/* Rendering */

function renderCalibration(payload) {
    if (state.pageClosing) {
        return;
    }

    const calibration = payload.calibration;

    if (
        calibration === null ||
        typeof calibration !== "object" ||
        Array.isArray(calibration)
    ) {
        throw new Error("Calibration API returned invalid data.");
    }

    renderSteering(calibration.steering ?? {});

    renderCameraMount(calibration.camera_mount ?? {});

    renderMotors(calibration.motors ?? {});

    renderGrayscale(calibration.grayscale ?? {});

    renderMetadata(payload);

    state.hasLoadedOnce = true;

    elements.loadingPanel.hidden = true;

    elements.errorPanel.hidden = true;

    elements.contentPanel.hidden = false;

    elements.refreshButton.disabled = false;

    elements.resetDefaultsButton.disabled = false;

    elements.refreshButton.textContent = "Refresh";

    setConnectionState("connected", "Connected");

    elements.announcement.textContent = "Calibration loaded.";

    setSteeringControlsDisabled(false);
    setCameraControlsDisabled(false);
    setMotorControlsDisabled(false);
    setGrayscaleControlsDisabled(false);

    renderSteeringEditor();
    renderCameraMountEditor();
    renderMotorEditor();
    renderGrayscaleEditor();
}

/* API */

async function loadCalibration() {
    if (state.pageClosing) {
        return;
    }

    showLoading();

    try {
        const payload = await requestJson("/api/calibration", {
            cache: "no-store",
            errorMessage: "Unable to load calibration.",
        });

        if (state.pageClosing) {
            return;
        }

        renderCalibration(payload);
    } catch (error) {
        if (state.pageClosing) {
            return;
        }

        showError(
            error instanceof Error
                ? error.message
                : "Unable to load calibration.",
        );
    }
}

async function resetCalibrationDefaults() {
    if (state.pageClosing) {
        return;
    }

    const confirmed = window.confirm(
        "Reset all robot calibration to safe defaults? " +
            "This resets steering, camera alignment, motor trim, " +
            "and line sensor calibration.",
    );

    if (!confirmed) {
        return;
    }

    elements.resetDefaultsButton.disabled = true;
    elements.refreshButton.disabled = true;

    elements.updatedTime.textContent = "Resetting calibration…";

    try {
        const payload = await requestJson("/api/calibration/reset", {
            method: "POST",
            errorMessage: "Unable to reset calibration.",
        });

        if (state.pageClosing) {
            return;
        }

        renderCalibration(payload);

        elements.announcement.textContent =
            "Calibration reset to safe defaults.";
    } catch (error) {
        if (state.pageClosing) {
            return;
        }

        const message =
            error instanceof Error
                ? error.message
                : "Unable to reset calibration.";

        elements.updatedTime.textContent = message;

        elements.announcement.textContent = message;
    } finally {
        if (!state.pageClosing) {
            elements.resetDefaultsButton.disabled = false;
            elements.refreshButton.disabled = false;
        }
    }
}

/* Shared UI */

function setupPageUI() {
    elements.refreshButton.addEventListener("click", () => {
        void loadCalibration();
    });

    elements.resetDefaultsButton.addEventListener("click", () => {
        void resetCalibrationDefaults();
    });

    elements.retryButton.addEventListener("click", () => {
        void loadCalibration();
    });
}

/* Cleanup */

function cleanupCalibrationPage() {
    if (state.pageClosing) {
        return;
    }

    state.pageClosing = true;

    if (state.steering.previewTimer !== null) {
        window.clearTimeout(state.steering.previewTimer);

        state.steering.previewTimer = null;
    }

    if (state.camera.previewTimer !== null) {
        window.clearTimeout(state.camera.previewTimer);

        state.camera.previewTimer = null;
    }
}

/* Initialization */

export function initializeCalibrationPage() {
    if (state.pageInitialized) {
        return;
    }

    state.pageInitialized = true;

    state.pageClosing = false;

    setupPageUI();

    setupSteering({
        renderCalibration,
    });

    setupCameraMount({
        renderCalibration,
    });

    setupMotors({
        renderCalibration,
    });

    setupGrayscale({
        renderCalibration,
    });

    window.addEventListener("pagehide", cleanupCalibrationPage);

    window.addEventListener("beforeunload", cleanupCalibrationPage);

    void loadCalibration();
}
