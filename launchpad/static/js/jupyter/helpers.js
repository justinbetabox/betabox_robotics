"use strict";

export function serviceStateLabel(state) {
    const labels = {
        active: "Running",
        inactive: "Stopped",
        failed: "Failed",
        activating: "Starting",
        deactivating: "Stopping",
    };

    return labels[state] ?? "Unknown";
}

export function buildJupyterUrl(port) {
    const { protocol, hostname, port: currentPort, origin } = window.location;

    // Through Nginx: keep JupyterHub on the same origin.
    if (currentPort === "" || currentPort === "80") {
        return new URL("/hub/", origin).href;
    }

    // Direct Launchpad access: preserve the original JupyterHub port.
    return `${protocol}//${hostname}:${port}/hub/`;
}
