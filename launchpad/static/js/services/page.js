"use strict";

import { requestServices } from "./api.js";

import { REFRESH_INTERVAL_MS } from "./constants.js";

import { elements } from "./dom.js";

import { formatTimestamp } from "./helpers.js";

import { renderAttention } from "./attention.js";

import { renderOverview } from "./overview.js";

import { renderServices } from "./services.js";

import { state } from "./state.js";

/* UI state */

function updateTimestamp() {
    elements.updated.textContent = `Last updated ${formatTimestamp(
        new Date(),
    )}`;
}

function clearTimestamp() {
    elements.updated.textContent = "Service status unavailable";
}

function setConnectionState(stateValue, label) {
    elements.connection.classList.remove(
        "status-unknown",
        "status-connecting",
        "status-connected",
        "status-error",
    );

    if (stateValue === "connected") {
        elements.connection.classList.add("status-connected");
    } else if (stateValue === "error") {
        elements.connection.classList.add("status-error");
    } else if (stateValue === "unknown") {
        elements.connection.classList.add("status-unknown");
    } else {
        elements.connection.classList.add("status-connecting");
    }

    elements.connection.textContent = label;
}

function setLoadingState(loading) {
    elements.refreshButton.disabled = loading;

    elements.retryButton.disabled = loading;

    elements.refreshButton.textContent = loading ? "Refreshing…" : "Refresh";

    if (loading) {
        setConnectionState("connecting", "Updating…");
    }
}

function showError(message) {
    elements.errorMessage.textContent = message;

    elements.errorPanel.hidden = false;

    setConnectionState("error", "Unavailable");
}

function hideError() {
    elements.errorPanel.hidden = true;
}

/* Rendering */

function renderPage(payload) {
    renderOverview(payload.summary);

    renderAttention(payload.services);

    renderServices(payload.services);
}

/* Services lifecycle */

async function loadServices() {
    if (state.requestInProgress) {
        return;
    }

    state.requestInProgress = true;

    setLoadingState(true);
    hideError();

    try {
        const payload = await requestServices();

        renderPage(payload);

        updateTimestamp();

        setConnectionState("connected", "Connected");
    } catch (error) {
        console.error("Unable to load services:", error);

        showError(
            error instanceof Error
                ? error.message
                : "The services API did not respond.",
        );

        clearTimestamp();
    } finally {
        state.requestInProgress = false;

        setLoadingState(false);
    }
}

/* Refresh lifecycle */

function startAutomaticRefresh() {
    stopAutomaticRefresh();

    state.refreshTimer = window.setInterval(() => {
        void loadServices();
    }, REFRESH_INTERVAL_MS);
}

function stopAutomaticRefresh() {
    if (state.refreshTimer === null) {
        return;
    }

    window.clearInterval(state.refreshTimer);

    state.refreshTimer = null;
}

/* Initialization */

export function initializeServicesPage() {
    elements.refreshButton.addEventListener("click", () => {
        void loadServices();
    });

    elements.retryButton.addEventListener("click", () => {
        void loadServices();
    });

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stopAutomaticRefresh();
            return;
        }

        startAutomaticRefresh();

        void loadServices();
    });

    window.addEventListener("beforeunload", stopAutomaticRefresh);

    startAutomaticRefresh();

    void loadServices();
}
