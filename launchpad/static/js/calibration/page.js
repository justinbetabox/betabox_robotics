"use strict";

import { elements } from "./dom.js";

import { setBadge } from "./helpers.js";

import { requestJson } from "./api.js";

import { state } from "./state.js";

import {
    renderSteering,
    renderSteeringEditor,
    restoreSavedSteering,
    setSteeringControlsDisabled,
    setupSteering,
} from "./steering.js";

import {
    renderCameraMount,
    renderCameraMountEditor,
    restoreSavedCameraMount,
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
    showLoading();

    try {
        const payload = await requestJson("/api/calibration", {
            cache: "no-store",
            errorMessage: "Unable to load calibration.",
        });

        renderCalibration(payload);
    } catch (error) {
        showError(
            error instanceof Error
                ? error.message
                : "Unable to load calibration.",
        );
    }
}

/* Shared UI */

function setupPageUI() {
    elements.refreshButton.addEventListener("click", () => {
        void loadCalibration();
    });

    elements.retryButton.addEventListener("click", () => {
        void loadCalibration();
    });
}

/* Cleanup */

function cleanupCalibrationPage() {
    restoreSavedSteering();
    restoreSavedCameraMount();
}

/* Initialization */

export function initializeCalibrationPage() {
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

    void loadCalibration();
}
