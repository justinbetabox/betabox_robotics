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
    let navigating = false;

    elements.openButton.addEventListener("click", async (event) => {
        if (elements.openButton.getAttribute("aria-disabled") === "true") {
            event.preventDefault();
            return;
        }

        // Keep normal navigation behavior for modified clicks.
        if (
            event.button !== 0 ||
            event.ctrlKey ||
            event.metaKey ||
            event.shiftKey ||
            event.altKey
        ) {
            return;
        }

        event.preventDefault();

        if (navigating) {
            return;
        }

        navigating = true;

        const destination = elements.openButton.href;

        elements.message.textContent = "Checking system clock…";

        let clockReady = false;

        try {
            clockReady = await window.betaboxClockReady;
        } catch {
            clockReady = false;
        }

        if (!clockReady) {
            elements.message.textContent =
                "Unable to verify the system clock. " +
                "Reload this page and try again.";

            navigating = false;
            return;
        }

        window.location.assign(destination);
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
