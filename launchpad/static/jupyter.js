"use strict";


function requireElement(selector) {
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


const statusBadge = requireElement(
    "#jupyter-status"
);

const healthDot = requireElement(
    "#jupyter-health-dot"
);

const serviceState = requireElement(
    "#jupyter-service-state"
);

const httpState = requireElement(
    "#jupyter-http-state"
);

const portValue = requireElement(
    "#jupyter-port"
);

const openButton = requireElement(
    "#open-jupyter"
);

const message = requireElement(
    "#jupyter-message"
);

let updateInProgress = false;


function setStatusClass(
    element,
    className,
) {
    element.classList.remove(
        "status-connecting",
        "status-unknown",
        "status-healthy",
        "status-warning",
        "status-error",
    );

    element.classList.add(
        className
    );
}


function serviceStateLabel(state) {
    switch (state) {
        case "active":
            return "Running";

        case "inactive":
            return "Stopped";

        case "failed":
            return "Failed";

        case "activating":
            return "Starting";

        case "deactivating":
            return "Stopping";

        default:
            return "Unknown";
    }
}


function buildJupyterUrl(port) {
    const protocol =
        window.location.protocol;

    const hostname =
        window.location.hostname;

    return (
        `${protocol}//${hostname}:${port}/hub/`
    );
}


function disableButton() {
    openButton.href = "#";

    openButton.classList.add(
        "is-disabled"
    );

    openButton.setAttribute(
        "aria-disabled",
        "true",
    );
}


function enableButton(port) {
    openButton.href =
        buildJupyterUrl(
            port
        );

    openButton.classList.remove(
        "is-disabled"
    );

    openButton.setAttribute(
        "aria-disabled",
        "false",
    );
}


async function updateStatus() {
    if (updateInProgress) {
        return;
    }

    updateInProgress = true;

    try {
        const response = await fetch(
            "/api/jupyter/status",
            {
                cache: "no-store",
            },
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data =
            await response.json();

        serviceState.textContent =
            serviceStateLabel(
                data.state
            );

        httpState.textContent =
            data.responding
                ? "Responding"
                : "Unavailable";

        portValue.textContent =
            String(data.port);

        if (
            data.active
            && data.responding
        ) {
            statusBadge.textContent =
                "Available";

            setStatusClass(
                statusBadge,
                "status-healthy",
            );

            setStatusClass(
                healthDot,
                "status-healthy",
            );

            enableButton(
                data.port
            );

            message.textContent =
                "JupyterLab is ready.";

            return;
        }

        disableButton();

        if (!data.active) {
            statusBadge.textContent =
                "Service Offline";

            setStatusClass(
                statusBadge,
                "status-error",
            );

            setStatusClass(
                healthDot,
                "status-error",
            );

            message.textContent =
                "JupyterHub is not running. "
                + "Ask a teacher to check the "
                + "platform services.";

            return;
        }

        statusBadge.textContent =
            "Not Responding";

        setStatusClass(
            statusBadge,
            "status-warning",
        );

        setStatusClass(
            healthDot,
            "status-warning",
        );

        message.textContent =
            "JupyterHub is running but its "
            + "web interface is not responding.";

    } catch (error) {
        disableButton();

        statusBadge.textContent =
            "Status Unavailable";

        setStatusClass(
            statusBadge,
            "status-error",
        );

        setStatusClass(
            healthDot,
            "status-error",
        );

        serviceState.textContent =
            "Unknown";

        httpState.textContent =
            "Unknown";

        portValue.textContent =
            "--";

        message.textContent =
            "Launchpad could not check "
            + "JupyterHub status.";

        console.error(
            "Jupyter status check failed:",
            error,
        );

    } finally {
        updateInProgress = false;
    }
}


openButton.addEventListener(
    "click",
    (event) => {
        if (
            openButton.getAttribute(
                "aria-disabled"
            ) === "true"
        ) {
            event.preventDefault();
        }
    },
);


document.addEventListener(
    "visibilitychange",
    () => {
        if (!document.hidden) {
            void updateStatus();
        }
    },
);


void updateStatus();

window.setInterval(
    () => {
        void updateStatus();
    },
    10000,
);
