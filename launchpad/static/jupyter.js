const statusBadge = document.querySelector(
    "#jupyter-status"
);

const healthDot = document.querySelector(
    "#jupyter-health-dot"
);

const serviceState = document.querySelector(
    "#jupyter-service-state"
);

const httpState = document.querySelector(
    "#jupyter-http-state"
);

const portValue = document.querySelector(
    "#jupyter-port"
);

const openButton = document.querySelector(
    "#open-jupyter"
);

const message = document.querySelector(
    "#jupyter-message"
);


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


function buildJupyterUrl(port) {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;

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
    openButton.href = buildJupyterUrl(
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

        const data = await response.json();

        serviceState.textContent = (
            data.state
        );

        httpState.textContent = (
            data.responding
                ? "responding"
                : "unavailable"
        );

        portValue.textContent = (
            String(data.port)
        );

        if (
            data.active
            && data.responding
        ) {
            statusBadge.textContent = (
                "Available"
            );

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

            message.textContent = (
                "JupyterLab is ready."
            );

            return;
        }

        disableButton();

        if (!data.active) {
            statusBadge.textContent = (
                "Service Offline"
            );

            setStatusClass(
                statusBadge,
                "status-error",
            );

            setStatusClass(
                healthDot,
                "status-error",
            );

            message.textContent = (
                "JupyterHub is not running. "
                + "Ask a teacher to check the "
                + "platform services."
            );

            return;
        }

        statusBadge.textContent = (
            "Not Responding"
        );

        setStatusClass(
            statusBadge,
            "status-warning",
        );

        setStatusClass(
            healthDot,
            "status-warning",
        );

        message.textContent = (
            "JupyterHub is running but its "
            + "web interface is not responding."
        );

    } catch (error) {
        disableButton();

        statusBadge.textContent = (
            "Status Unavailable"
        );

        setStatusClass(
            statusBadge,
            "status-error",
        );

        setStatusClass(
            healthDot,
            "status-error",
        );

        serviceState.textContent = (
            "unknown"
        );

        httpState.textContent = (
            "unknown"
        );

        message.textContent = (
            "Launchpad could not check "
            + "JupyterHub status."
        );

        console.error(
            "Jupyter status check failed:",
            error,
        );
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


updateStatus();

window.setInterval(
    updateStatus,
    10000,
);
