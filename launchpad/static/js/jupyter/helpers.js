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
    const protocol = window.location.protocol;

    const hostname = window.location.hostname;

    return `${protocol}//` + `${hostname}:${port}/hub/`;
}
