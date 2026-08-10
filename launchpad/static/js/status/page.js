"use strict";

import { AUTO_REFRESH_INTERVAL_MS } from "./constants.js";

import { elements } from "./dom.js";

import { updateTimestamp } from "./helpers.js";

import { renderAttention } from "./attention.js";

import { renderHardware } from "./hardware.js";

import { renderNetwork } from "./network.js";

import { renderOverview } from "./overview.js";

import { renderSystem } from "./system.js";

import { requestStatus } from "./api.js";

import { state } from "./state.js";

/* UI state */

function markStatusStale() {
    elements.updatedTime.textContent = "Status may be out of date.";
}

function setConnectionState(stateValue, text) {
    elements.connectionStatus.classList.remove(
        "status-connecting",
        "status-connected",
        "status-error",
    );

    elements.connectionStatus.classList.add(`status-${stateValue}`);

    elements.connectionStatus.textContent = text;
}

function showError(message) {
    elements.errorMessage.textContent = message;

    elements.errorPanel.hidden = false;
}

function hideError() {
    elements.errorPanel.hidden = true;
}

/* Rendering */

function renderStatus(data) {
    renderOverview(data);
    renderAttention(data);
    renderHardware(data);
    renderSystem(data);
    renderNetwork(data);

    updateTimestamp(elements.updatedTime);
}

/* API */

async function loadStatus() {
    if (state.requestInProgress) {
        return;
    }

    state.requestInProgress = true;

    elements.refreshButton.disabled = true;

    elements.refreshButton.textContent = "Refreshing…";

    setConnectionState("connecting", "Updating…");

    try {
        const data = await requestStatus();

        renderStatus(data);
        hideError();

        setConnectionState("connected", "Connected");
    } catch (error) {
        console.error("Unable to load platform status:", error);

        markStatusStale();

        showError(
            error instanceof Error
                ? error.message
                : "Unable to load platform status.",
        );

        setConnectionState("error", "Unavailable");
    } finally {
        state.requestInProgress = false;

        elements.refreshButton.disabled = false;

        elements.refreshButton.textContent = "Refresh";
    }
}

/* Refresh lifecycle */

function startAutomaticRefresh() {
    stopAutomaticRefresh();

    state.refreshTimer = window.setInterval(() => {
        void loadStatus();
    }, AUTO_REFRESH_INTERVAL_MS);
}

function stopAutomaticRefresh() {
    if (state.refreshTimer === null) {
        return;
    }

    window.clearInterval(state.refreshTimer);

    state.refreshTimer = null;
}

/* Initialization */

export function initializeStatusPage() {
    elements.refreshButton.addEventListener("click", () => {
        void loadStatus();
    });

    elements.retryButton.addEventListener("click", () => {
        void loadStatus();
    });

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stopAutomaticRefresh();
            return;
        }

        startAutomaticRefresh();

        void loadStatus();
    });

    window.addEventListener("beforeunload", stopAutomaticRefresh);

    startAutomaticRefresh();

    void loadStatus();
}
