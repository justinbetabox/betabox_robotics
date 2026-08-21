"use strict";

import { elements } from "./dom.js";

import { setBadge, showTemporaryMessage } from "./helpers.js";

import { requestJson } from "./api.js";

import { state } from "./state.js";

const MIN_CALIBRATION_SPAN = 100;

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

function calibrationSpanValid(floor, line) {
    if (floor === null || line === null) {
        return false;
    }

    if (floor.length !== 3 || line.length !== 3) {
        return false;
    }

    return floor.every(
        (floorValue, index) =>
            Math.abs(floorValue - line[index]) >= MIN_CALIBRATION_SPAN,
    );
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

    const valid =
        complete &&
        calibrationSpanValid(state.grayscale.floor, state.grayscale.line);

    const changed =
        !sensorValuesEqual(state.grayscale.floor, state.grayscale.savedFloor) ||
        !sensorValuesEqual(state.grayscale.line, state.grayscale.savedLine);

    elements.grayscale.saveButton.disabled = !valid || !changed;

    elements.grayscale.resetButton.disabled = !changed;

    elements.grayscale.clearButton.disabled = !state.grayscale.calibrated;

    if (!changed) {
        elements.grayscale.message.textContent = "";
        return;
    }

    if (!complete) {
        elements.grayscale.message.textContent =
            "Capture both surfaces before saving.";
        return;
    }

    if (!valid) {
        elements.grayscale.message.textContent =
            "Floor and line readings must differ " +
            `by at least ${MIN_CALIBRATION_SPAN} ` +
            "on every sensor.";

        return;
    }

    elements.grayscale.message.textContent = "Unsaved line sensor calibration.";
}

/* Sampling */

async function sampleGrayscale() {
    if (state.pageClosing) {
        return null;
    }

    const payload = await requestJson("/api/calibration/grayscale/sample", {
        cache: "no-store",
        invalidMessage: "Line sensor API returned " + "an invalid response.",
        errorMessage: "Unable to read the " + "line sensor.",
    });

    if (state.pageClosing) {
        return null;
    }

    const values = copySensorValues(payload.values);

    if (values === null) {
        throw new Error("Line sensor returned " + "invalid readings.");
    }

    return values;
}

async function captureGrayscaleFloor() {
    if (state.pageClosing) {
        return;
    }

    setGrayscaleControlsDisabled(true);

    elements.refreshButton.disabled = true;

    elements.grayscale.message.textContent = "Reading floor surface…";

    try {
        const values = await sampleGrayscale();

        if (state.pageClosing || values === null) {
            return;
        }

        state.grayscale.floor = values;

        renderGrayscaleEditor();

        elements.announcement.textContent = "Floor reference captured.";
    } catch (error) {
        if (state.pageClosing) {
            return;
        }

        renderGrayscaleEditor();

        elements.grayscale.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to capture " + "floor reference.";
    } finally {
        if (!state.pageClosing) {
            setGrayscaleControlsDisabled(false);

            elements.refreshButton.disabled = false;
        }
    }
}

async function captureGrayscaleLine() {
    if (state.pageClosing) {
        return;
    }

    setGrayscaleControlsDisabled(true);

    elements.refreshButton.disabled = true;

    elements.grayscale.message.textContent = "Reading line surface…";

    try {
        const values = await sampleGrayscale();

        if (state.pageClosing || values === null) {
            return;
        }

        state.grayscale.line = values;

        renderGrayscaleEditor();

        elements.announcement.textContent = "Line reference captured.";
    } catch (error) {
        if (state.pageClosing) {
            return;
        }

        renderGrayscaleEditor();

        elements.grayscale.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to capture " + "line reference.";
    } finally {
        if (!state.pageClosing) {
            setGrayscaleControlsDisabled(false);

            elements.refreshButton.disabled = false;
        }
    }
}

/* Persistence */

async function saveGrayscale(renderCalibration) {
    if (state.pageClosing) {
        return;
    }

    if (state.grayscale.floor === null || state.grayscale.line === null) {
        elements.grayscale.message.textContent =
            "Capture both surfaces before saving.";

        return;
    }

    if (!calibrationSpanValid(state.grayscale.floor, state.grayscale.line)) {
        elements.grayscale.message.textContent =
            "Floor and line readings are too similar. " +
            `They must differ by at least ${MIN_CALIBRATION_SPAN} ` +
            "on every sensor.";

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
            errorMessage: "Unable to save line " + "sensor calibration.",
        });

        if (state.pageClosing) {
            return;
        }

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
        if (state.pageClosing) {
            return;
        }

        renderGrayscaleEditor();

        elements.grayscale.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to save line " + "sensor calibration.";
    } finally {
        if (!state.pageClosing) {
            elements.refreshButton.disabled = false;
        }
    }
}

async function clearGrayscale(renderCalibration) {
    if (state.pageClosing) {
        return;
    }

    elements.grayscale.clearButton.disabled = true;

    elements.refreshButton.disabled = true;

    elements.grayscale.message.textContent =
        "Clearing line sensor calibration…";

    try {
        const payload = await requestJson("/api/calibration/grayscale/clear", {
            method: "POST",
            errorMessage: "Unable to clear line " + "sensor calibration.",
        });

        if (state.pageClosing) {
            return;
        }

        renderCalibration(payload);

        showTemporaryMessage(
            elements.grayscale.message,
            "Line sensor calibration cleared.",
            () => !state.grayscale.calibrated,
        );

        elements.announcement.textContent = "Line sensor calibration cleared.";
    } catch (error) {
        if (state.pageClosing) {
            return;
        }

        renderGrayscaleEditor();

        elements.grayscale.message.textContent =
            error instanceof Error
                ? error.message
                : "Unable to clear line " + "sensor calibration.";
    } finally {
        if (!state.pageClosing) {
            elements.refreshButton.disabled = false;
        }
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
        if (state.pageClosing) {
            return;
        }

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
        if (state.pageClosing) {
            return;
        }

        void captureGrayscaleFloor();
    });

    elements.grayscale.captureLineButton.addEventListener("click", () => {
        if (state.pageClosing) {
            return;
        }

        void captureGrayscaleLine();
    });

    elements.grayscale.saveButton.addEventListener("click", () => {
        if (state.pageClosing) {
            return;
        }

        void saveGrayscale(renderCalibration);
    });

    elements.grayscale.clearButton.addEventListener("click", () => {
        if (state.pageClosing) {
            return;
        }

        void clearGrayscale(renderCalibration);
    });
}
