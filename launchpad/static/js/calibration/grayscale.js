"use strict";

import { elements } from "./dom.js";

import { setBadge, showTemporaryMessage } from "./helpers.js";

import { requestJson } from "./api.js";

import { state } from "./state.js";

/* Helpers */

function copySensorValues(values) {
    if (!Array.isArray(values) || values.length !== 3) {
        return null;
    }

    const numbers = values.map((value) => Number(value));

    return numbers.every(Number.isFinite) ? numbers : null;
}

function sensorValuesEqual(first, second) {
    if (first === null || second === null) {
        return first === second;
    }

    return first.every((value, index) => value === second[index]);
}

function renderSensorValues(element, values) {
    const validValues = copySensorValues(values);

    element.replaceChildren();

    const displayedValues = validValues ?? [null, null, null];

    for (const value of displayedValues) {
        const item = document.createElement("span");

        item.textContent =
            value === null
                ? "—"
                : Number.isInteger(value)
                  ? String(value)
                  : value.toFixed(1);

        element.appendChild(item);
    }
}

/* Rendering */

export function renderGrayscale(grayscale) {
    state.grayscale.calibrated = Boolean(grayscale.calibrated);

    state.grayscale.savedFloor = state.grayscale.calibrated
        ? copySensorValues(grayscale.floor)
        : null;

    state.grayscale.savedLine = state.grayscale.calibrated
        ? copySensorValues(grayscale.line)
        : null;

    state.grayscale.floor =
        state.grayscale.savedFloor === null
            ? null
            : [...state.grayscale.savedFloor];

    state.grayscale.line =
        state.grayscale.savedLine === null
            ? null
            : [...state.grayscale.savedLine];

    renderGrayscaleEditor();

    setBadge(
        elements.grayscale.status,
        state.grayscale.calibrated ? "Calibrated" : "Not Calibrated",
        state.grayscale.calibrated ? "healthy" : "warning",
    );
}

export function renderGrayscaleEditor() {
    renderSensorValues(elements.grayscale.floor, state.grayscale.floor);

    renderSensorValues(elements.grayscale.line, state.grayscale.line);

    const complete =
        state.grayscale.floor !== null && state.grayscale.line !== null;

    const changed =
        !sensorValuesEqual(state.grayscale.floor, state.grayscale.savedFloor) ||
        !sensorValuesEqual(state.grayscale.line, state.grayscale.savedLine);

    elements.grayscale.saveButton.disabled = !complete || !changed;

    elements.grayscale.resetButton.disabled = !changed;

    elements.grayscale.clearButton.disabled = !state.grayscale.calibrated;

    elements.grayscale.message.textContent = changed
        ? complete
            ? "Unsaved line sensor " + "calibration."
            : "Capture both surfaces " + "before saving."
        : "";
}

/* Sampling */

async function sampleGrayscale() {
    const payload = await requestJson("/api/calibration/grayscale/sample", {
        cache: "no-store",
        invalidMessage: "Line sensor API returned " + "an invalid response.",
        errorMessage: "Unable to read the line sensor.",
    });

    const values = copySensorValues(payload.values);

    if (values === null) {
        throw new Error("Line sensor returned " + "invalid readings.");
    }

    return values;
}

async function captureGrayscaleFloor() {
    setGrayscaleControlsDisabled(true);

    elements.refreshButton.disabled = true;

    elements.grayscale.message.textContent = "Reading floor surface…";

    try {
        state.grayscale.floor = await sampleGrayscale();

        renderGrayscaleEditor();

        elements.grayscale.message.textContent = "Floor reference captured.";

        elements.announcement.textContent = "Floor reference captured.";
    } catch (error) {
        renderGrayscaleEditor();

        elements.grayscale.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to capture " + "floor reference.";
    } finally {
        setGrayscaleControlsDisabled(false);

        elements.refreshButton.disabled = false;
    }
}

async function captureGrayscaleLine() {
    setGrayscaleControlsDisabled(true);

    elements.refreshButton.disabled = true;

    elements.grayscale.message.textContent = "Reading line surface…";

    try {
        state.grayscale.line = await sampleGrayscale();

        renderGrayscaleEditor();

        elements.grayscale.message.textContent = "Line reference captured.";

        elements.announcement.textContent = "Line reference captured.";
    } catch (error) {
        renderGrayscaleEditor();

        elements.grayscale.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to capture " + "line reference.";
    } finally {
        setGrayscaleControlsDisabled(false);

        elements.refreshButton.disabled = false;
    }
}

/* Persistence */

async function saveGrayscale(renderCalibration) {
    if (state.grayscale.floor === null || state.grayscale.line === null) {
        elements.grayscale.message.textContent =
            "Capture both surfaces before saving.";

        return;
    }

    elements.grayscale.saveButton.disabled = true;

    elements.grayscale.resetButton.disabled = true;

    elements.refreshButton.disabled = true;

    elements.grayscale.message.textContent = "Saving line sensor calibration…";

    try {
        const payload = await requestJson("/api/calibration/grayscale", {
            method: "PUT",
            body: {
                floor: state.grayscale.floor,
                line: state.grayscale.line,
            },
            errorMessage: "Unable to save line sensor " + "calibration.",
        });

        renderCalibration(payload);

        showTemporaryMessage(
            elements.grayscale.message,
            "Line sensor calibration saved.",
            () =>
                sensorValuesEqual(
                    state.grayscale.floor,
                    state.grayscale.savedFloor,
                ) &&
                sensorValuesEqual(
                    state.grayscale.line,
                    state.grayscale.savedLine,
                ),
        );

        elements.announcement.textContent = "Line sensor calibration saved.";
    } catch (error) {
        renderGrayscaleEditor();

        elements.grayscale.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to save line sensor " + "calibration.";
    } finally {
        elements.refreshButton.disabled = false;
    }
}

async function clearGrayscale(renderCalibration) {
    elements.grayscale.clearButton.disabled = true;

    elements.refreshButton.disabled = true;

    elements.grayscale.message.textContent =
        "Clearing line sensor calibration…";

    try {
        const payload = await requestJson("/api/calibration/grayscale/clear", {
            method: "POST",
            errorMessage: "Unable to clear line sensor " + "calibration.",
        });

        renderCalibration(payload);

        showTemporaryMessage(
            elements.grayscale.message,
            "Line sensor calibration cleared.",
            () => !state.grayscale.calibrated,
        );

        elements.announcement.textContent = "Line sensor calibration cleared.";
    } catch (error) {
        renderGrayscaleEditor();

        elements.grayscale.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to clear line sensor " + "calibration.";
    } finally {
        elements.refreshButton.disabled = false;
    }
}

/* Controls */

export function setGrayscaleControlsDisabled(disabled) {
    elements.grayscale.captureFloorButton.disabled = disabled;

    elements.grayscale.captureLineButton.disabled = disabled;

    if (disabled) {
        elements.grayscale.saveButton.disabled = true;

        elements.grayscale.resetButton.disabled = true;

        elements.grayscale.clearButton.disabled = true;
    }
}

/* Setup */

export function setupGrayscale({ renderCalibration }) {
    if (typeof renderCalibration !== "function") {
        throw new TypeError("renderCalibration must be a function");
    }

    elements.grayscale.resetButton.addEventListener("click", () => {
        state.grayscale.floor =
            state.grayscale.savedFloor === null
                ? null
                : [...state.grayscale.savedFloor];

        state.grayscale.line =
            state.grayscale.savedLine === null
                ? null
                : [...state.grayscale.savedLine];

        renderGrayscaleEditor();

        elements.grayscale.message.textContent =
            "Line sensor changes discarded.";
    });

    elements.grayscale.captureFloorButton.addEventListener("click", () => {
        void captureGrayscaleFloor();
    });

    elements.grayscale.captureLineButton.addEventListener("click", () => {
        void captureGrayscaleLine();
    });

    elements.grayscale.saveButton.addEventListener("click", () => {
        void saveGrayscale(renderCalibration);
    });

    elements.grayscale.clearButton.addEventListener("click", () => {
        void clearGrayscale(renderCalibration);
    });
}
