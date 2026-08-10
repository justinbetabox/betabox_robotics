"use strict";

import { VideoConnection } from "./webrtc.js";

/* Constants */

const VISION_OFFER_API_URL = "/api/vision/offer";

const VIDEO_STATE_LABELS = {
    connecting: "Connecting…",
    connected: "Live",
    disconnected: "Reconnecting…",
    error: "Unavailable",
    closed: "Disconnected",
};

const VIDEO_STATE_CLASSES = {
    connecting: "status-connecting",
    connected: "status-connected",
    disconnected: "status-disconnected",
    error: "status-error",
    closed: "status-disconnected",
};

const VIDEO_STATE_MESSAGES = {
    connecting: "Connecting vision…",
    connected: "",
    disconnected: "Reconnecting vision…",
    error: "Vision unavailable",
    closed: "Vision disconnected",
};

/* Page state */

let videoConnection = null;

/* DOM */

function requireElement(selector, expectedType = HTMLElement) {
    const element = document.querySelector(selector);

    if (!(element instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return element;
}

const video = requireElement("#live-vision", HTMLVideoElement);

const status = requireElement("#vision-status");

const view = requireElement(".vision-view");

const message = requireElement(".vision-message");

/* Rendering */

function setVideoState(state) {
    const stateValue = Object.hasOwn(VIDEO_STATE_LABELS, state)
        ? state
        : "error";

    view.dataset.videoState = stateValue;

    status.classList.remove(
        "status-connecting",
        "status-connected",
        "status-disconnected",
        "status-error",
    );

    status.classList.add(VIDEO_STATE_CLASSES[stateValue]);

    status.textContent = VIDEO_STATE_LABELS[stateValue];

    message.textContent = VIDEO_STATE_MESSAGES[stateValue];
}

/* Lifecycle */

function initializeVisionPage() {
    if (videoConnection !== null) {
        return;
    }

    videoConnection = new VideoConnection(video, VISION_OFFER_API_URL, {
        onStateChange: setVideoState,
    });

    void videoConnection.connect();
}

function closeVisionPage() {
    if (videoConnection === null) {
        return;
    }

    const connection = videoConnection;

    videoConnection = null;

    void connection.close();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeVisionPage, {
        once: true,
    });
} else {
    initializeVisionPage();
}

window.addEventListener("pagehide", closeVisionPage);

window.addEventListener("beforeunload", closeVisionPage);
