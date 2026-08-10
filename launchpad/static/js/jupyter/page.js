"use strict";

import { requestJupyterStatus } from "./api.js";

import { STATUS_REFRESH_INTERVAL_MS } from "./constants.js";

import { elements } from "./dom.js";

import {
    renderAvailable,
    renderLoading,
    renderNotResponding,
    renderServiceInfo,
    renderServiceOffline,
    renderUnavailable,
} from "./render.js";

import { state } from "./state.js";

async function loadJupyterStatus({ showLoading = false } = {}) {
    if (state.requestInProgress) {
        return;
    }

    state.requestInProgress = true;

    if (showLoading) {
        renderLoading();
    }

    try {
        const data = await requestJupyterStatus();

        renderServiceInfo(data);

        if (data.active && data.responding) {
            renderAvailable(data);
        } else if (!data.active) {
            renderServiceOffline();
        } else {
            renderNotResponding();
        }
    } catch (error) {
        renderUnavailable();

        console.error("Jupyter status check failed:", error);
    } finally {
        state.requestInProgress = false;
    }
}

/* UI */

function setupUI() {
    elements.openButton.addEventListener("click", (event) => {
        if (elements.openButton.getAttribute("aria-disabled") === "true") {
            event.preventDefault();
        }
    });
}

/* Refresh lifecycle */

function startAutomaticRefresh() {
    stopAutomaticRefresh();

    state.refreshTimer = window.setInterval(() => {
        void loadJupyterStatus();
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

export function initializeJupyterPage() {
    setupUI();

    startAutomaticRefresh();

    void loadJupyterStatus({
        showLoading: true,
    });
}

/* Page lifecycle */

document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        stopAutomaticRefresh();
        return;
    }

    startAutomaticRefresh();

    void loadJupyterStatus();
});

window.addEventListener("beforeunload", stopAutomaticRefresh);
