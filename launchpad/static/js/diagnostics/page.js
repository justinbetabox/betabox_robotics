"use strict";

import { requestDiagnostics } from "./api.js";

import { elements } from "./dom.js";

import { formatTimestamp } from "./helpers.js";

import { renderIssues } from "./issues.js";

import { renderOverview } from "./overview.js";

import { renderDiagnoses } from "./results.js";

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

function setRunningState(running) {
    elements.runButton.disabled = running;

    elements.retryButton.disabled = running;

    elements.runButton.textContent = running ? "Running…" : "Run";

    if (running) {
        setConnectionState("connecting", "Running…");
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
    elements.updated.textContent = `Last completed ${formatTimestamp(
        new Date(),
    )}`;
}

function clearTimestamp() {
    elements.updated.textContent = "Diagnostics unavailable";
}

/* Rendering */

function renderLoadingState() {
    elements.updated.textContent = "Running platform diagnostics…";

    elements.issuesSection.hidden = true;

    elements.issuesList.replaceChildren();

    elements.issuesSummary.textContent = "";

    elements.diagnosticsList.replaceChildren();

    const loading = document.createElement("div");

    loading.className = "empty-state diagnostics-empty";

    loading.textContent = "Running platform diagnostics…";

    elements.diagnosticsList.append(loading);
}

function renderDiagnostics(payload) {
    renderOverview(payload.summary);

    renderIssues(payload.summary, payload.diagnoses);

    renderDiagnoses(payload.diagnoses);
}

/* Diagnostics lifecycle */

async function runDiagnostics() {
    if (state.requestInProgress) {
        return;
    }

    state.requestInProgress = true;

    setRunningState(true);

    hideError();

    if (!state.hasCompletedRun) {
        renderLoadingState();
    } else {
        elements.updated.textContent = "Running platform diagnostics…";
    }

    try {
        const payload = await requestDiagnostics();

        renderDiagnostics(payload);

        state.hasCompletedRun = true;

        updateTimestamp();

        setConnectionState("connected", "Complete");
    } catch (error) {
        console.error("Unable to run diagnostics:", error);

        showError(
            error instanceof Error
                ? error.message
                : "The diagnostics API did not respond.",
        );

        clearTimestamp();
    } finally {
        state.requestInProgress = false;

        setRunningState(false);
    }
}

/* Initialization */

export function initializeDiagnosticsPage() {
    elements.runButton.addEventListener("click", () => {
        void runDiagnostics();
    });

    elements.retryButton.addEventListener("click", () => {
        void runDiagnostics();
    });
}
