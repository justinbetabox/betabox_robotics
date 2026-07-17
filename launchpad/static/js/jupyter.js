"use strict";

const JUPYTER_STATUS_URL = (
    "/api/jupyter/status"
);


function requireElement(
    selector
) {
    const found = document.querySelector(
        selector
    );

    if (found === null) {
        throw new Error(
            `Missing required element: ${selector}`
        );
    }

    return found;
}


const elements = {
    status: requireElement(
        "#jupyter-status"
    ),

    healthDot: requireElement(
        "#jupyter-health-dot"
    ),

    serviceState: requireElement(
        "#jupyter-service-state"
    ),

    httpState: requireElement(
        "#jupyter-http-state"
    ),

    port: requireElement(
        "#jupyter-port"
    ),

    openButton: requireElement(
        "#open-jupyter"
    ),

    message: requireElement(
        "#jupyter-message"
    ),
};

let updateInProgress = false;
let updateTimer = null;


function setStatusClass(
    element,
    className
) {
    element.classList.remove(
        "status-connecting",
        "status-connected",
        "status-healthy",
        "status-warning",
        "status-error",
        "status-unknown"
    );

    element.classList.add(
        className
    );
}


function serviceStateLabel(
    state
) {
    const labels = {
        active: "Running",
        inactive: "Stopped",
        failed: "Failed",
        activating: "Starting",
        deactivating: "Stopping",
    };

    return labels[state] || "Unknown";
}


function buildJupyterUrl(
    port
) {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;

    return (
        `${protocol}//${hostname}:${port}/hub/`
    );
}


function disableButton() {
    elements.openButton.href = "#";

    elements.openButton.classList.add(
        "is-disabled"
    );

    elements.openButton.setAttribute(
        "aria-disabled",
        "true"
    );

    elements.openButton.setAttribute(
        "tabindex",
        "-1"
    );
}


function enableButton(
    port
) {
    elements.openButton.href = (
        buildJupyterUrl(port)
    );

    elements.openButton.classList.remove(
        "is-disabled"
    );

    elements.openButton.setAttribute(
        "aria-disabled",
        "false"
    );

    elements.openButton.removeAttribute(
        "tabindex"
    );
}


function renderAvailable(
    data
) {
    elements.status.textContent = "Available";

    setStatusClass(
        elements.status,
        "status-connected"
    );

    setStatusClass(
        elements.healthDot,
        "status-healthy"
    );

    enableButton(data.port);

    elements.message.textContent = (
        "JupyterLab is ready."
    );
}


function renderServiceOffline() {
    elements.status.textContent = (
        "Service Offline"
    );

    setStatusClass(
        elements.status,
        "status-error"
    );

    setStatusClass(
        elements.healthDot,
        "status-error"
    );

    disableButton();

    elements.message.textContent = (
        "JupyterHub is not running. "
        + "Ask a teacher to check the "
        + "platform services."
    );
}


function renderNotResponding() {
    elements.status.textContent = (
        "Not Responding"
    );

    setStatusClass(
        elements.status,
        "status-warning"
    );

    setStatusClass(
        elements.healthDot,
        "status-warning"
    );

    disableButton();

    elements.message.textContent = (
        "JupyterHub is running but its "
        + "web interface is not responding."
    );
}


function renderUnavailable() {
    elements.status.textContent = (
        "Status Unavailable"
    );

    setStatusClass(
        elements.status,
        "status-error"
    );

    setStatusClass(
        elements.healthDot,
        "status-error"
    );

    elements.serviceState.textContent = (
        "Unknown"
    );

    elements.httpState.textContent = (
        "Unknown"
    );

    elements.port.textContent = "--";

    disableButton();

    elements.message.textContent = (
        "Launchpad could not check "
        + "JupyterHub status."
    );
}


function validatePayload(
    data
) {
    if (
        !data
        || typeof data !== "object"
    ) {
        throw new Error(
            "The Jupyter status API returned "
            + "an invalid response."
        );
    }

    if (
        typeof data.active !== "boolean"
        || typeof data.responding !== "boolean"
    ) {
        throw new Error(
            "The Jupyter status response is "
            + "missing availability information."
        );
    }

    const port = Number(data.port);

    if (
        !Number.isInteger(port)
        || port < 1
        || port > 65535
    ) {
        throw new Error(
            "The Jupyter status response "
            + "contains an invalid port."
        );
    }
}


async function updateStatus() {
    if (updateInProgress) {
        return;
    }

    updateInProgress = true;

    try {
        const response = await fetch(
            JUPYTER_STATUS_URL,
            {
                method: "GET",
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            }
        );

        if (!response.ok) {
            throw new Error(
                `Jupyter status API returned `
                + `HTTP ${response.status}.`
            );
        }

        const data = await response.json();

        validatePayload(data);

        elements.serviceState.textContent = (
            serviceStateLabel(data.state)
        );

        elements.httpState.textContent = (
            data.responding
                ? "Responding"
                : "Unavailable"
        );

        elements.port.textContent = (
            String(data.port)
        );

        if (
            data.active
            && data.responding
        ) {
            renderAvailable(data);
        } else if (!data.active) {
            renderServiceOffline();
        } else {
            renderNotResponding();
        }
    } catch (error) {
        renderUnavailable();

        console.error(
            "Jupyter status check failed:",
            error
        );
    } finally {
        updateInProgress = false;
    }
}


function initializeJupyterPage() {
    elements.openButton.addEventListener(
        "click",
        event => {
            if (
                elements.openButton.getAttribute(
                    "aria-disabled"
                ) === "true"
            ) {
                event.preventDefault();
            }
        }
    );

    document.addEventListener(
        "visibilitychange",
        () => {
            if (!document.hidden) {
                void updateStatus();
            }
        }
    );

    void updateStatus();

    updateTimer = window.setInterval(
        () => {
            if (!document.hidden) {
                void updateStatus();
            }
        },
        10000
    );
}


function cleanupJupyterPage() {
    if (updateTimer !== null) {
        window.clearInterval(
            updateTimer
        );

        updateTimer = null;
    }
}


window.addEventListener(
    "beforeunload",
    cleanupJupyterPage
);


if (
    document.readyState === "loading"
) {
    document.addEventListener(
        "DOMContentLoaded",
        initializeJupyterPage
    );
} else {
    initializeJupyterPage();
}
