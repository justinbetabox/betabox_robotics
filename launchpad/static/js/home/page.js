"use strict";

import { requestStatus } from "./api.js";

import { STATUS_REFRESH_INTERVAL_MS } from "./constants.js";

import { configureHudToggle, renderDisconnected, renderStatus } from "./hud.js";

import { state } from "./state.js";

/* Status lifecycle */

async function loadStatus() {
    if (state.requestInProgress) {
        return;
    }

    state.requestInProgress = true;

    try {
        const status = await requestStatus();

        renderStatus(status);
    } catch (error) {
        console.error("Unable to load home status:", error);

        renderDisconnected();
    } finally {
        state.requestInProgress = false;
    }
}

/* Refresh lifecycle */

function startAutomaticRefresh() {
    stopAutomaticRefresh();

    state.refreshTimer = window.setInterval(() => {
        void loadStatus();
    }, STATUS_REFRESH_INTERVAL_MS);
}

function stopAutomaticRefresh() {
    if (state.refreshTimer === null) {
        return;
    }

    window.clearInterval(state.refreshTimer);

    state.refreshTimer = null;
}

/* Initialization */

export function initializeHomePage() {
    configureHudToggle();

    startAutomaticRefresh();

    void loadStatus();
}

/* Page lifecycle */

document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        stopAutomaticRefresh();
        return;
    }

    startAutomaticRefresh();

    void loadStatus();
});

window.addEventListener("beforeunload", stopAutomaticRefresh);
