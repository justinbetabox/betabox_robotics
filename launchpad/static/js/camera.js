import {
    VideoConnection,
} from "./webrtc.js";


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

let videoConnection = null;


function setVideoState(
    state
) {
    view.dataset.videoState = state;

    const labels = {
        connecting: "Connecting…",
        connected: "Connected",
        disconnected: "Reconnecting…",
        error: "Unavailable",
        closed: "Disconnected",
    };

    const classes = {
        connecting: "status-connecting",
        connected: "status-connected",
        disconnected: "status-disconnected",
        error: "status-error",
        closed: "status-disconnected",
    };

    status.classList.remove(
        "status-connecting",
        "status-connected",
        "status-disconnected",
        "status-error"
    );

    status.classList.add(
        classes[state]
        ?? "status-error"
    );

    status.textContent = (
        labels[state]
        ?? "Unknown"
    );

    message.textContent = (
        {
            connecting:
                "Connecting camera…",

            connected:
                "",

            disconnected:
                "Reconnecting camera…",

            error:
                "Camera unavailable",

            closed:
                "Camera disconnected",
        }[state]
        ?? "Camera status unknown"
    );
}


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


window.addEventListener(
    "beforeunload",
    () => {
        if (videoConnection !== null) {
            void videoConnection.close();
        }
    }
);
