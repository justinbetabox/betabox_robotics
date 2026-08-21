"use strict";

function requireElement(selector, expectedType = HTMLElement) {
    const element = document.querySelector(selector);

    if (!(element instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return element;
}

export const elements = {
    connectionStatus: requireElement("#calibration-connection"),

    refreshButton: requireElement("#refresh-calibration"),

    resetDefaultsButton: requireElement("#reset-calibration-defaults"),

    retryButton: requireElement("#retry-calibration"),

    loadingPanel: requireElement("#calibration-loading"),

    contentPanel: requireElement("#calibration-content"),

    errorPanel: requireElement("#calibration-error"),

    errorMessage: requireElement("#calibration-error-message"),

    sourceBadge: requireElement("#calibration-source"),

    updatedTime: requireElement("#calibration-updated"),

    announcement: requireElement("#calibration-announcement"),

    steering: {
        offset: requireElement("#steering-offset"),

        status: requireElement("#steering-status"),

        increaseButton: requireElement("#steering-increase"),

        decreaseButton: requireElement("#steering-decrease"),

        saveButton: requireElement("#steering-save"),

        resetButton: requireElement("#steering-reset"),

        message: requireElement("#steering-message"),
    },

    camera: {
        panOffset: requireElement("#camera-pan-offset"),

        tiltOffset: requireElement("#camera-tilt-offset"),

        status: requireElement("#camera-status"),

        panIncreaseButton: requireElement("#camera-pan-increase"),

        panDecreaseButton: requireElement("#camera-pan-decrease"),

        tiltIncreaseButton: requireElement("#camera-tilt-increase"),

        tiltDecreaseButton: requireElement("#camera-tilt-decrease"),

        saveButton: requireElement("#camera-save"),

        resetButton: requireElement("#camera-reset"),

        message: requireElement("#camera-message"),
    },

    motors: {
        leftTrim: requireElement("#left-motor-trim"),

        rightTrim: requireElement("#right-motor-trim"),

        status: requireElement("#motors-status"),

        leftIncreaseButton: requireElement("#left-trim-increase"),

        leftDecreaseButton: requireElement("#left-trim-decrease"),

        rightIncreaseButton: requireElement("#right-trim-increase"),

        rightDecreaseButton: requireElement("#right-trim-decrease"),

        saveButton: requireElement("#motors-save"),

        resetButton: requireElement("#motors-reset"),

        previewButton: requireElement("#motors-preview"),

        message: requireElement("#motors-message"),
    },

    grayscale: {
        status: requireElement("#grayscale-status"),

        floor: requireElement("#grayscale-floor"),

        line: requireElement("#grayscale-line"),

        captureFloorButton: requireElement("#grayscale-capture-floor"),

        captureLineButton: requireElement("#grayscale-capture-line"),

        saveButton: requireElement("#grayscale-save"),

        resetButton: requireElement("#grayscale-reset"),

        clearButton: requireElement("#grayscale-clear"),

        message: requireElement("#grayscale-message"),
    },
};
