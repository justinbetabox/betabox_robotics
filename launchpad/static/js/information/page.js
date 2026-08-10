"use strict";

import { requestInformation } from "./api.js";

import { REFRESH_INTERVAL_MS } from "./constants.js";

import { elements } from "./dom.js";

import { renderFeatures, renderMedia } from "./features.js";

import { formatUpdatedTime } from "./helpers.js";

import { renderNetwork } from "./network.js";

import { initializePreferences } from "./preferences.js";

import { renderRobot } from "./robot.js";

import { renderSoftware } from "./software.js";

import { state } from "./state.js";

import { renderStorage } from "./storage.js";

/* UI state */

function updateTimestamp() {
    elements.updated.textContent = `Last updated ${formatUpdatedTime(
        new Date(),
    )}`;
}

function clearTimestamp() {
    elements.updated.textContent = "Information unavailable";
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

function renderInformation(payload) {
    renderRobot(payload.robot);

    renderNetwork(payload.network);

    renderSoftware(payload.software);

    renderStorage(payload.storage);

    renderMedia(payload.media);

    renderFeatures(payload.features);
}

/* Information lifecycle */

async function loadInformation() {
    if (state.requestInProgress) {
        return;
    }

    state.requestInProgress = true;

    setLoadingState(true);
    hideError();

    try {
        const payload = await requestInformation();

        renderInformation(payload);

        updateTimestamp();

        setConnectionState("connected", "Connected");
    } catch (error) {
        console.error("Unable to load platform information:", error);

        showError(
            error instanceof Error
                ? error.message
                : "The Information API " + "did not respond.",
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
        void loadInformation();
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

export function initializeInformationPage() {
    elements.refreshButton.addEventListener("click", () => {
        void loadInformation();
    });

    elements.retryButton.addEventListener("click", () => {
        void loadInformation();
    });

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stopAutomaticRefresh();
            return;
        }

        startAutomaticRefresh();

        void loadInformation();
    });

    window.addEventListener("beforeunload", stopAutomaticRefresh);

    void initializePreferences();

    startAutomaticRefresh();

    void loadInformation();
}
