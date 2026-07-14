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


function setVideoState(state) {
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
        error: "status-disconnected",
        closed: "status-disconnected",
    };

    status.className =
        `camera-status ${classes[state]}`;

    status.textContent =
        labels[state] ?? "Unknown";

    message.textContent =
        {
            connecting: "Connecting camera…",
            connected: "",
            disconnected: "Reconnecting camera…",
            error: "Camera unavailable",
            closed: "Camera disconnected",
        }[state] ?? "";
}


document.addEventListener(
    "DOMContentLoaded",
    () => {
        videoConnection =
            new VideoConnection(
                video,
                "/api/vision/offer",
                {
                    onStateChange:
                        setVideoState,
                }
            );

        void videoConnection.connect();
    }
);


window.addEventListener(
    "beforeunload",
    () => {
        if (videoConnection !== null) {
            void videoConnection.close();
        }
    }
);
