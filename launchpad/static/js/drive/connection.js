"use strict";

import { HEARTBEAT_INTERVAL_MS } from "./constants.js";

import { elements } from "./dom.js";

import {
    resetLocalControls,
    sendDriveState,
    sendJson,
    stopAndResetControls,
} from "./commands.js";

import { state } from "./state.js";

function setConnectionState(label, cssClass) {
    elements.connection.className = `connection-status ${cssClass}`;

    elements.connection.textContent = label;

    const hudLabels = {
        "status-connecting": "Connecting",
        "status-connected": "Connected",
        "status-busy": "Busy",
        "status-paused": "Paused",
        "status-disconnected": "Disconnected",
    };

    elements.driveStatus.textContent = hudLabels[cssClass] ?? label;
}

export class DriveConnection {
    constructor(url) {
        this.url = url;

        this.websocket = null;

        this.heartbeatTimer = null;

        this.reconnectTimer = null;

        this.reconnectDelayMs = 750;

        this.resumeRequested = false;
    }

    connect() {
        if (state.pageClosing || document.hidden) {
            return;
        }

        if (
            this.websocket !== null &&
            (this.websocket.readyState === WebSocket.OPEN ||
                this.websocket.readyState === WebSocket.CONNECTING)
        ) {
            return;
        }

        this.cancelReconnect();

        state.controlPaused = false;

        setConnectionState("Connecting…", "status-connecting");

        const websocket = new WebSocket(this.url);

        this.websocket = websocket;

        state.websocket = websocket;

        websocket.addEventListener("open", () => {
            if (websocket !== this.websocket) {
                return;
            }

            setConnectionState("Requesting Control…", "status-connecting");
        });

        websocket.addEventListener("message", (event) => {
            this.handleMessage(websocket, event);
        });

        websocket.addEventListener("close", (event) => {
            this.handleClose(websocket, event);
        });

        websocket.addEventListener("error", () => {
            if (websocket !== this.websocket) {
                return;
            }

            setConnectionState("Connection Error", "status-disconnected");
        });
    }

    handleMessage(websocket, event) {
        if (websocket !== this.websocket) {
            return;
        }

        let message;

        try {
            message = JSON.parse(event.data);
        } catch (error) {
            console.error("Invalid Drive WebSocket message:", error);

            return;
        }

        if (
            message === null ||
            typeof message !== "object" ||
            Array.isArray(message)
        ) {
            console.error("Invalid Drive WebSocket payload.");

            return;
        }

        const messageType = message.type;

        if (typeof messageType !== "string") {
            console.error("Drive WebSocket message type is invalid.");

            return;
        }

        if (messageType === "ready") {
            state.ready = true;

            state.controlPaused = false;

            setConnectionState("Control Active", "status-connected");

            elements.owner.textContent = "You have control";

            this.startHeartbeat();

            sendDriveState(true);

            return;
        }

        if (messageType === "busy") {
            state.ready = false;

            setConnectionState("Robot Busy", "status-busy");

            elements.owner.textContent =
                typeof message.message === "string"
                    ? message.message
                    : "The robot is already in use.";

            return;
        }

        if (messageType === "unavailable") {
            state.ready = false;

            setConnectionState("Robot In Use", "status-busy");

            elements.owner.textContent =
                typeof message.message === "string"
                    ? message.message
                    : "Robot control is unavailable.";

            return;
        }

        if (messageType === "stopped") {
            resetLocalControls();

            return;
        }

        if (messageType === "error") {
            const messageText =
                typeof message.message === "string"
                    ? message.message
                    : "Manual Drive reported an error.";

            console.error(messageText);

            stopAndResetControls();
        }
    }

    handleClose(websocket, event) {
        if (websocket !== this.websocket) {
            return;
        }

        this.stopHeartbeat();

        this.websocket = null;

        state.websocket = null;

        state.ready = false;

        resetLocalControls();

        const shouldResume =
            this.resumeRequested && !document.hidden && !state.pageClosing;

        this.resumeRequested = false;

        if (state.pageClosing) {
            return;
        }

        if (shouldResume) {
            this.connect();

            return;
        }

        if (state.controlPaused || document.hidden) {
            setConnectionState("Control Paused", "status-paused");

            elements.owner.textContent =
                "Control paused while this tab is inactive.";

            return;
        }

        if (event.code === 4002) {
            setConnectionState("Robot In Use", "status-busy");

            elements.owner.textContent =
                "The robot is currently being used " +
                "by another application.";

            return;
        }

        if (event.code === 4001) {
            setConnectionState("Robot Busy", "status-busy");

            elements.owner.textContent =
                "The robot is already being controlled " +
                "from another browser.";

            return;
        }

        if (event.code === 4003) {
            setConnectionState("Control Lost", "status-paused");

            elements.owner.textContent =
                "Drive control expired because " + "heartbeats stopped.";

            this.scheduleReconnect();

            return;
        }

        setConnectionState("Disconnected", "status-disconnected");

        elements.owner.textContent = "Drive control disconnected";

        this.scheduleReconnect();
    }

    suspend() {
        if (state.pageClosing || state.controlPaused) {
            return;
        }

        state.controlPaused = true;

        this.resumeRequested = false;

        stopAndResetControls();

        this.stopHeartbeat();

        this.cancelReconnect();

        const websocket = this.websocket;

        if (websocket !== null && websocket.readyState === WebSocket.OPEN) {
            websocket.close(1000, "manual drive tab inactive");
        } else if (
            websocket !== null &&
            websocket.readyState === WebSocket.CONNECTING
        ) {
            websocket.close();
        }

        setConnectionState("Control Paused", "status-paused");

        elements.owner.textContent =
            "Control paused while this tab is inactive.";
    }

    resume() {
        if (state.pageClosing || document.hidden) {
            return;
        }

        state.controlPaused = false;

        this.resumeRequested = true;

        setConnectionState("Reconnecting…", "status-connecting");

        elements.owner.textContent = "Requesting robot control…";

        if (
            this.websocket !== null &&
            this.websocket.readyState === WebSocket.CLOSING
        ) {
            return;
        }

        this.resumeRequested = false;

        this.connect();
    }

    shutdown() {
        state.pageClosing = true;

        state.controlPaused = false;

        stopAndResetControls();

        this.stopHeartbeat();

        this.cancelReconnect();

        const websocket = this.websocket;

        state.ready = false;

        state.websocket = null;

        if (
            websocket !== null &&
            (websocket.readyState === WebSocket.OPEN ||
                websocket.readyState === WebSocket.CONNECTING)
        ) {
            websocket.close(1000, "manual drive page closed");
        }

        this.websocket = null;
    }

    startHeartbeat() {
        this.stopHeartbeat();

        this.heartbeatTimer = window.setInterval(() => {
            if (state.ready && !document.hidden) {
                sendJson({
                    type: "heartbeat",
                });
            }
        }, HEARTBEAT_INTERVAL_MS);
    }

    stopHeartbeat() {
        if (this.heartbeatTimer === null) {
            return;
        }

        window.clearInterval(this.heartbeatTimer);

        this.heartbeatTimer = null;
    }

    scheduleReconnect() {
        if (
            state.pageClosing ||
            state.controlPaused ||
            document.hidden ||
            this.reconnectTimer !== null
        ) {
            return;
        }

        this.reconnectTimer = window.setTimeout(() => {
            this.reconnectTimer = null;

            this.connect();
        }, this.reconnectDelayMs);
    }

    cancelReconnect() {
        if (this.reconnectTimer === null) {
            return;
        }

        window.clearTimeout(this.reconnectTimer);

        this.reconnectTimer = null;
    }
}
