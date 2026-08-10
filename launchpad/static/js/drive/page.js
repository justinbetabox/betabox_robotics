"use strict";

import { initializeCameraControls } from "./camera.js";

import { emergencyStop, stopAndResetControls } from "./commands.js";

import { DriveConnection } from "./connection.js";

import {
    DRIVE_WEBSOCKET_PATH,
    STATUS_REFRESH_INTERVAL_MS,
} from "./constants.js";

import { elements } from "./dom.js";

import { initializeDriveControls } from "./joystick.js";

import { state } from "./state.js";

import { refreshPlatformStatus } from "./status.js";

import { DriveVideoConnection } from "./video.js";

function driveWebSocketUrl() {
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";

    return `${scheme}://` + window.location.host + DRIVE_WEBSOCKET_PATH;
}

export class ManualDriveSession {
    constructor() {
        this.driveConnection = null;

        this.videoConnection = null;

        this.statusTimer = null;

        this.started = false;
    }

    start() {
        if (this.started) {
            return;
        }

        this.started = true;

        this.configureControls();

        this.initializeVideo();

        this.initializeDriveConnection();

        this.configureLifecycle();

        this.startStatusRefresh();
    }

    configureControls() {
        initializeDriveControls();

        initializeCameraControls();

        elements.emergencyStopButton.addEventListener("click", emergencyStop);
    }

    initializeVideo() {
        this.videoConnection = new DriveVideoConnection();

        this.videoConnection.connect();
    }

    initializeDriveConnection() {
        this.driveConnection = new DriveConnection(driveWebSocketUrl());

        this.driveConnection.connect();
    }

    startStatusRefresh() {
        this.stopStatusRefresh();

        void refreshPlatformStatus();

        this.statusTimer = window.setInterval(() => {
            if (!document.hidden) {
                void refreshPlatformStatus();
            }
        }, STATUS_REFRESH_INTERVAL_MS);
    }

    stopStatusRefresh() {
        if (this.statusTimer === null) {
            return;
        }

        window.clearInterval(this.statusTimer);

        this.statusTimer = null;
    }

    suspend() {
        if (!this.started) {
            return;
        }

        this.driveConnection?.suspend();
    }

    resume() {
        if (!this.started || document.hidden || state.pageClosing) {
            return;
        }

        this.driveConnection?.resume();

        void refreshPlatformStatus();
    }

    stopMotion() {
        stopAndResetControls();
    }

    shutdown() {
        if (!this.started) {
            return;
        }

        this.started = false;

        this.stopStatusRefresh();

        this.driveConnection?.shutdown();

        this.driveConnection = null;

        if (this.videoConnection !== null) {
            void this.videoConnection.close();

            this.videoConnection = null;
        }
    }

    configureLifecycle() {
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                this.suspend();
                return;
            }

            this.resume();
        });

        window.addEventListener("blur", () => {
            this.stopMotion();
        });

        window.addEventListener("pagehide", () => {
            this.shutdown();
        });

        window.addEventListener("beforeunload", () => {
            this.shutdown();
        });
    }
}

let manualDriveSession = null;

export function initializeDrivePage() {
    if (manualDriveSession !== null) {
        return;
    }

    manualDriveSession = new ManualDriveSession();

    manualDriveSession.start();
}
