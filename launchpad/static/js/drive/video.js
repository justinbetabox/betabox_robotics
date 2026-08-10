"use strict";

import { VISION_OFFER_API_URL } from "./constants.js";

import { elements } from "./dom.js";

import { VideoConnection } from "../webrtc.js";

function setVideoState(state) {
    elements.videoPanel.dataset.videoState = state;

    const labels = {
        connecting: "Connecting camera…",

        connected: "Camera connected",

        disconnected: "Reconnecting camera…",

        error: "Camera unavailable",

        closed: "Camera disconnected",
    };

    elements.videoStatus.textContent = labels[state] ?? "Camera";

    const hudLabels = {
        connecting: "Connecting",

        connected: "Connected",

        disconnected: "Reconnecting",

        error: "Unavailable",

        closed: "Disconnected",
    };

    elements.cameraStatus.textContent = hudLabels[state] ?? "Unknown";
}

export class DriveVideoConnection {
    constructor() {
        this.connection = null;
    }

    connect() {
        if (this.connection !== null) {
            return;
        }

        this.connection = new VideoConnection(
            elements.video,
            VISION_OFFER_API_URL,
            {
                onStateChange: setVideoState,
            },
        );

        this.connection.connect();
    }

    async close() {
        if (this.connection === null) {
            return;
        }

        const connection = this.connection;

        this.connection = null;

        await connection.close();
    }
}
