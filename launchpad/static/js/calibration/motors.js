"use strict";

import {
    MOTOR_TRIM_MAX,
    MOTOR_TRIM_MIN,
    MOTOR_TRIM_STEP,
} from "./constants.js";

import { elements } from "./dom.js";

import {
    clamp,
    formatTrim,
    setBadge,
    showTemporaryMessage,
} from "./helpers.js";

import { requestJson } from "./api.js";

import { state } from "./state.js";

/* Rendering */

export function renderMotors(motors) {
    const left = Number(motors.left_trim);

    const right = Number(motors.right_trim);

    const validLeft = Number.isFinite(left) ? left : 1;

    const validRight = Number.isFinite(right) ? right : 1;

    state.motors.savedLeftTrim = validLeft;

    state.motors.savedRightTrim = validRight;

    state.motors.leftTrim = validLeft;

    state.motors.rightTrim = validRight;

    renderMotorEditor();

    const adjusted = validLeft !== 1 || validRight !== 1;

    setBadge(
        elements.motors.status,
        adjusted ? "Adjusted" : "Default",
        adjusted ? "healthy" : "neutral",
    );
}

export function renderMotorEditor() {
    elements.motors.leftTrim.textContent = formatTrim(state.motors.leftTrim);

    elements.motors.rightTrim.textContent = formatTrim(state.motors.rightTrim);

    const changed =
        state.motors.leftTrim !== state.motors.savedLeftTrim ||
        state.motors.rightTrim !== state.motors.savedRightTrim;

    elements.motors.saveButton.disabled = !changed;

    elements.motors.resetButton.disabled = !changed;

    elements.motors.message.textContent = changed
        ? "Unsaved motor trim changes."
        : "";
}

/* Preview */

async function previewMotorTrim() {
    await requestJson("/api/calibration/motors/preview", {
        method: "POST",
        body: {
            left_trim: state.motors.leftTrim,
            right_trim: state.motors.rightTrim,
        },
        invalidMessage: "Motor trim API returned " + "an invalid response.",
        errorMessage: "Unable to preview motor trim.",
    });
}

async function runMotorPreview() {
    setMotorControlsDisabled(true);

    elements.refreshButton.disabled = true;

    elements.motors.message.textContent = "Previewing motor trim…";

    try {
        await previewMotorTrim();
    } catch (error) {
        elements.motors.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to preview " + "motor trim.";
    } finally {
        setMotorControlsDisabled(false);

        elements.refreshButton.disabled = false;

        renderMotorEditor();
    }
}

/* Persistence */

async function saveMotors(renderCalibration) {
    elements.motors.saveButton.disabled = true;

    elements.motors.resetButton.disabled = true;

    elements.refreshButton.disabled = true;

    elements.motors.message.textContent = "Saving…";

    try {
        const payload = await requestJson("/api/calibration/motors", {
            method: "PUT",
            body: {
                left_trim: state.motors.leftTrim,
                right_trim: state.motors.rightTrim,
            },
            errorMessage: "Unable to save motor trim " + "calibration.",
        });

        renderCalibration(payload);

        showTemporaryMessage(
            elements.motors.message,
            "Motor trim calibration saved.",
            () =>
                state.motors.leftTrim === state.motors.savedLeftTrim &&
                state.motors.rightTrim === state.motors.savedRightTrim,
        );

        elements.announcement.textContent = "Motor trim calibration saved.";
    } catch (error) {
        renderMotorEditor();

        elements.motors.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to save motor trim " + "calibration.";
    } finally {
        elements.refreshButton.disabled = false;
    }
}

/* Controls */

export function setMotorControlsDisabled(disabled) {
    elements.motors.leftIncreaseButton.disabled = disabled;

    elements.motors.leftDecreaseButton.disabled = disabled;

    elements.motors.rightIncreaseButton.disabled = disabled;

    elements.motors.rightDecreaseButton.disabled = disabled;

    elements.motors.previewButton.disabled = disabled;

    if (disabled) {
        elements.motors.saveButton.disabled = true;

        elements.motors.resetButton.disabled = true;
    }
}

/* Setup */

export function setupMotors({ renderCalibration }) {
    if (typeof renderCalibration !== "function") {
        throw new TypeError("renderCalibration must be a function");
    }

    elements.motors.leftIncreaseButton.addEventListener("click", () => {
        state.motors.leftTrim = clamp(
            Number((state.motors.leftTrim + MOTOR_TRIM_STEP).toFixed(2)),
            MOTOR_TRIM_MIN,
            MOTOR_TRIM_MAX,
        );

        renderMotorEditor();
    });

    elements.motors.leftDecreaseButton.addEventListener("click", () => {
        state.motors.leftTrim = clamp(
            Number((state.motors.leftTrim - MOTOR_TRIM_STEP).toFixed(2)),
            MOTOR_TRIM_MIN,
            MOTOR_TRIM_MAX,
        );

        renderMotorEditor();
    });

    elements.motors.rightIncreaseButton.addEventListener("click", () => {
        state.motors.rightTrim = clamp(
            Number((state.motors.rightTrim + MOTOR_TRIM_STEP).toFixed(2)),
            MOTOR_TRIM_MIN,
            MOTOR_TRIM_MAX,
        );

        renderMotorEditor();
    });

    elements.motors.rightDecreaseButton.addEventListener("click", () => {
        state.motors.rightTrim = clamp(
            Number((state.motors.rightTrim - MOTOR_TRIM_STEP).toFixed(2)),
            MOTOR_TRIM_MIN,
            MOTOR_TRIM_MAX,
        );

        renderMotorEditor();
    });

    elements.motors.resetButton.addEventListener("click", () => {
        state.motors.leftTrim = state.motors.savedLeftTrim;

        state.motors.rightTrim = state.motors.savedRightTrim;

        renderMotorEditor();

        elements.motors.message.textContent = "Motor trim changes discarded.";
    });

    elements.motors.previewButton.addEventListener("click", () => {
        void runMotorPreview();
    });

    elements.motors.saveButton.addEventListener("click", () => {
        void saveMotors(renderCalibration);
    });
}
