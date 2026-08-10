"use strict";

import { elements } from "./dom.js";

import { buildJupyterUrl, serviceStateLabel } from "./helpers.js";

function setStatusClass(element, className) {
    element.classList.remove(
        "status-connecting",
        "status-connected",
        "status-healthy",
        "status-warning",
        "status-error",
        "status-unknown",
    );

    element.classList.add(className);
}

function disableButton() {
    elements.openButton.href = "#";

    elements.openButton.classList.add("is-disabled");

    elements.openButton.setAttribute("aria-disabled", "true");

    elements.openButton.setAttribute("tabindex", "-1");
}

function enableButton(port) {
    elements.openButton.href = buildJupyterUrl(port);

    elements.openButton.classList.remove("is-disabled");

    elements.openButton.setAttribute("aria-disabled", "false");

    elements.openButton.removeAttribute("tabindex");
}

export function renderLoading() {
    elements.status.textContent = "Loading…";

    setStatusClass(elements.status, "status-connecting");

    disableButton();

    elements.message.textContent = "Checking JupyterHub…";
}

export function renderAvailable(data) {
    elements.status.textContent = "Live";

    setStatusClass(elements.status, "status-connected");

    enableButton(data.port);

    elements.message.textContent = "JupyterLab is ready.";
}

export function renderServiceOffline() {
    elements.status.textContent = "Service Offline";

    setStatusClass(elements.status, "status-error");

    disableButton();

    elements.message.textContent =
        "JupyterHub is not running. " +
        "Ask a teacher to check the " +
        "platform services.";
}

export function renderNotResponding() {
    elements.status.textContent = "Not Responding";

    setStatusClass(elements.status, "status-warning");

    disableButton();

    elements.message.textContent =
        "JupyterHub is running but its " + "web interface is not responding.";
}

export function renderUnavailable() {
    elements.status.textContent = "Status Unavailable";

    setStatusClass(elements.status, "status-error");

    elements.serviceState.textContent = "Unknown";

    elements.httpState.textContent = "Unknown";

    elements.port.textContent = "--";

    disableButton();

    elements.message.textContent =
        "Launchpad could not check " + "JupyterHub status.";
}

export function renderServiceInfo(data) {
    elements.serviceState.textContent = serviceStateLabel(data.state);

    elements.httpState.textContent = data.responding
        ? "Responding"
        : "Unavailable";

    elements.port.textContent = String(data.port);
}
