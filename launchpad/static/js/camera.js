"use strict";

import {
    VideoConnection,
} from "./webrtc.js";

/* Constants */

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


/* DOM elements */

const video = document.getElementById(
    "live-camera"
);

const status = document.getElementById(
    "camera-status"
);

const view = document.querySelector(
    ".camera-view"
);

const message = document.querySelector(
    ".camera-message"
);


/* UI Helpers */

function setVideoState(
    state
) {
    view.dataset.videoState = state;

    status.classList.remove(
        "status-connecting",
        "status-connected",
        "status-disconnected",
        "status-error"
    );

    status.classList.add(
        VIDEO_STATE_CLASSES[state]
        ?? "status-error"
    );

    status.textContent = (
        VIDEO_STATE_LABELS[state]
        ?? "Unknown"
    );

    message.textContent = (
        VIDEO_STATE_MESSAGES[state]
        ?? "Vision status unknown"
    );
}


/* Initialization */

function initializeCameraPage() {
    videoConnection = (
        new VideoConnection(
            video,
            "/api/vision/offer",
            {
                onStateChange:
                    setVideoState,
            }
        )
    );

    void videoConnection.connect();
}


if (
    document.readyState === "loading"
) {
    document.addEventListener(
        "DOMContentLoaded",
        initializeCameraPage
    );
} else {
    initializeCameraPage();
}


/* Cleanup */

window.addEventListener(
    "beforeunload",
    () => {
        if (videoConnection !== null) {
            void videoConnection.close();
        }
    }
);
