"use strict";

import { STEERING_MAX, STEERING_MIN, STEERING_STEP } from "./constants.js";

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

export function renderSteering(steering) {
    const offset = Number(steering.offset);

    const validOffset = Number.isFinite(offset) ? offset : 0;

    state.steering.savedOffset = validOffset;

    state.steering.offset = validOffset;

    renderSteeringEditor();

    const adjusted = validOffset !== 0;

    setBadge(
        elements.steering.status,
        adjusted ? "Adjusted" : "Default",
        adjusted ? "healthy" : "neutral",
    );
}

export function renderSteeringEditor() {
    elements.steering.offset.textContent = formatOffset(state.steering.offset);

    const changed = state.steering.offset !== state.steering.savedOffset;

    elements.steering.saveButton.disabled = !changed;

    elements.steering.resetButton.disabled = !changed;

    elements.steering.message.textContent = changed
        ? "Unsaved steering changes."
        : "";
}

/* Preview */

async function previewSteering() {
    await requestJson("/api/calibration/steering/preview", {
        method: "POST",
        body: {
            offset: state.steering.offset,
        },
        invalidMessage: "Steering API returned " + "an invalid response.",
        errorMessage: "Unable to move steering.",
    });
}

function scheduleSteeringPreview() {
    if (state.steering.previewTimer !== null) {
        window.clearTimeout(state.steering.previewTimer);
    }

    state.steering.previewTimer = window.setTimeout(async () => {
        state.steering.previewTimer = null;

        setSteeringControlsDisabled(true);

        try {
            await previewSteering();
        } catch (error) {
            elements.steering.message.textContent =
                error instanceof Error
                    ? error.message
                    : "Unable to move " + "steering.";
        } finally {
            setSteeringControlsDisabled(false);

            renderSteeringEditor();
        }
    }, 75);
}

/* Persistence */

async function saveSteering(renderCalibration) {
    elements.steering.saveButton.disabled = true;

    elements.steering.resetButton.disabled = true;

    elements.refreshButton.disabled = true;

    elements.steering.message.textContent = "Saving…";

    try {
        const payload = await requestJson("/api/calibration/steering", {
            method: "PUT",
            body: {
                offset: state.steering.offset,
            },
            errorMessage: "Unable to save steering " + "calibration.",
        });

        renderCalibration(payload);

        showTemporaryMessage(
            elements.steering.message,
            "Steering calibration saved.",
            () => state.steering.offset === state.steering.savedOffset,
        );

        elements.announcement.textContent = "Steering calibration saved.";
    } catch (error) {
        renderSteeringEditor();

        elements.steering.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to save steering " + "calibration.";
    } finally {
        elements.refreshButton.disabled = false;
    }
}

/* Cleanup */

export function restoreSavedSteering() {
    if (state.steering.previewTimer !== null) {
        window.clearTimeout(state.steering.previewTimer);

        state.steering.previewTimer = null;
    }

    if (state.steering.offset === state.steering.savedOffset) {
        return;
    }

    fetch("/api/calibration/steering/preview", {
        method: "POST",
        keepalive: true,
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify({
            offset: state.steering.savedOffset,
        }),
    }).catch(() => {
        /*
         * The page is leaving, so there is
         * nowhere useful to display an error.
         */
    });
}

/* Controls */

export function setSteeringControlsDisabled(disabled) {
    elements.steering.increaseButton.disabled = disabled;

    elements.steering.decreaseButton.disabled = disabled;

    if (disabled) {
        elements.steering.saveButton.disabled = true;

        elements.steering.resetButton.disabled = true;
    }
}

/* Setup */

export function setupSteering({ renderCalibration }) {
    if (typeof renderCalibration !== "function") {
        throw new TypeError("renderCalibration must be a function");
    }

    elements.steering.increaseButton.addEventListener("click", () => {
        state.steering.offset = clamp(
            state.steering.offset + STEERING_STEP,
            STEERING_MIN,
            STEERING_MAX,
        );

        renderSteeringEditor();
        scheduleSteeringPreview();
    });

    elements.steering.decreaseButton.addEventListener("click", () => {
        state.steering.offset = clamp(
            state.steering.offset - STEERING_STEP,
            STEERING_MIN,
            STEERING_MAX,
        );

        renderSteeringEditor();
        scheduleSteeringPreview();
    });

    elements.steering.resetButton.addEventListener("click", () => {
        state.steering.offset = state.steering.savedOffset;

        renderSteeringEditor();
        scheduleSteeringPreview();
    });

    elements.steering.saveButton.addEventListener("click", () => {
        void saveSteering(renderCalibration);
    });
}
