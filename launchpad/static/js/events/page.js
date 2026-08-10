"use strict";

import { requestEvents } from "./api.js";

import { REFRESH_INTERVAL_MS } from "./constants.js";

import { elements } from "./dom.js";

import { renderEvents } from "./events.js";

import { clearFilters, renderComponentOptions } from "./filters.js";

import { formatUpdatedTime } from "./helpers.js";

import { renderOverview } from "./overview.js";

import { state } from "./state.js";

/* UI state */

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

function updateTimestamp() {
    elements.updated.textContent = `Last updated ${formatUpdatedTime(
        new Date(),
    )}`;
}

function clearTimestamp() {
    elements.updated.textContent = "Events unavailable";
}

/* Rendering */

function renderLoadingState() {
    elements.updated.textContent = "Loading platform events…";

    elements.listSummary.textContent = "Loading…";

    elements.eventsList.setAttribute("aria-busy", "true");

    elements.eventsList.replaceChildren();

    const loading = document.createElement("div");

    loading.className = "empty-state events-empty";

    loading.textContent = "Loading platform events…";

    elements.eventsList.append(loading);
}

function renderPage(payload) {
    renderOverview(payload.summary);

    renderComponentOptions(payload.components);

    renderEvents(payload.events, payload.summary);
}

/* Events lifecycle */

async function loadEvents() {
    if (state.requestInProgress) {
        return;
    }

    state.requestInProgress = true;

    setLoadingState(true);

    hideError();

    if (!state.hasLoadedOnce) {
        renderLoadingState();
    }

    try {
        const payload = await requestEvents();

        renderPage(payload);

        state.hasLoadedOnce = true;

        updateTimestamp();

        setConnectionState("connected", "Connected");
    } catch (error) {
        console.error("Unable to load events:", error);

        showError(
            error instanceof Error
                ? error.message
                : "The Events API did not respond.",
        );

        clearTimestamp();

        elements.eventsList.setAttribute("aria-busy", "false");
    } finally {
        state.requestInProgress = false;

        setLoadingState(false);
    }
}

/* Refresh lifecycle */

function startAutomaticRefresh() {
    stopAutomaticRefresh();

    state.refreshTimer = window.setInterval(() => {
        void loadEvents();
    }, REFRESH_INTERVAL_MS);
}

function stopAutomaticRefresh() {
    if (state.refreshTimer === null) {
        return;
    }

    window.clearInterval(state.refreshTimer);

    state.refreshTimer = null;
}

/* UI */

function setupEventListeners() {
    elements.refreshButton.addEventListener("click", () => {
        void loadEvents();
    });

    elements.retryButton.addEventListener("click", () => {
        void loadEvents();
    });

    elements.clearButton.addEventListener("click", () => {
        clearFilters();

        void loadEvents();
    });

    elements.filterForm.addEventListener("submit", (event) => {
        event.preventDefault();

        void loadEvents();
    });
}

/* Initialization */

export function initializeEventsPage() {
    setupEventListeners();

    startAutomaticRefresh();

    void loadEvents();
}

/* Page lifecycle */

document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        stopAutomaticRefresh();
        return;
    }

    startAutomaticRefresh();

    void loadEvents();
});

window.addEventListener("beforeunload", stopAutomaticRefresh);
