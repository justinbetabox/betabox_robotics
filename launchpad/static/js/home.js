"use strict";


/* Constants */

const STATUS_REFRESH_INTERVAL_MS = 5000;


/* Page state */
let requestInProgress = false;
let refreshTimer = null;


/* DOM helpers */

const element = (id) => (
    document.getElementById(id)
);


/* Data helpers */

function objectValue(
    object,
    ...path
) {
    let current = object;

    for (const key of path) {
        if (
            current === null
            || current === undefined
            || typeof current !== "object"
        ) {
            return undefined;
        }

        current = current[key];
    }

    return current;
}

function firstDefined(
    ...values
) {
    return values.find(
        (value) => (
            value !== undefined
            && value !== null
        )
    );
}


/* Formatting */

function formatVoltage(value) {
    const voltage = Number(value);

    if (!Number.isFinite(voltage)) {
        return "--";
    }

    return `${voltage.toFixed(2)} V`;
}

function formatTemperature(value) {
    const temperature = Number(value);

    if (!Number.isFinite(temperature)) {
        return "--";
    }

    return `${temperature.toFixed(1)} °C`;
}

function formatPercent(value) {
    const percent = Number(value);

    if (!Number.isFinite(percent)) {
        return "--";
    }

    return `${percent.toFixed(0)}%`;
}


/* Classification */

function controlLabel(status) {
    const control = (
        objectValue(
            status,
            "control",
        ) ?? {}
    );

    if (control.available === true) {
        return "Available";
    }

    if (control.owner) {
        const owner = String(
            control.owner,
        );

        const normalized = owner.toLowerCase();

        if (
            normalized.includes(
                "manual drive",
            )
        ) {
            return "Manual Drive";
        }

        if (
            normalized.includes(
                "python",
            )
        ) {
            return "Python App";
        }

        return owner;
    }

    if (control.available === false) {
        return "In Use";
    }

    return "Unavailable";
}

function visionLabel(status) {
    const vision = (
        objectValue(
            status,
            "hardware",
            "vision",
        )
        ?? {}
    );

    if (!vision.service_available) {
        return "Unavailable";
    }

    if (
        vision.camera_running
        && vision.camera_has_frame
    ) {
        return "Ready";
    }

    if (
        vision.running
        || vision.camera_running
    ) {
        return "Starting";
    }

    return "Offline";
}

function networkLabel(status) {
    const ethernetConnected = firstDefined(
        objectValue(
            status,
            "system_health",
            "ethernet",
            "connected",
        ),
        false,
    );

    const wifiConnected = firstDefined(
        objectValue(
            status,
            "system_health",
            "wifi",
            "connected",
        ),
        false,
    );

    if (ethernetConnected) {
        return "Ethernet";
    }

    if (wifiConnected) {
        return "Wi-Fi";
    }

    return "Disconnected";
}

function jupyterLabel(status) {
    const active = firstDefined(
        objectValue(
            status,
            "jupyterhub",
            "active",
        ),
        false,
    );

    const responding = firstDefined(
        objectValue(
            status,
            "jupyterhub",
            "responding",
        ),
        false,
    );

    const state = String(
        firstDefined(
            objectValue(
                status,
                "jupyterhub",
                "state",
            ),
            "unknown",
        )
    ).toLowerCase();

    if (
        active
        && responding
    ) {
        return "Ready";
    }

    if (
        state === "activating"
        || state === "reloading"
    ) {
        return "Starting";
    }

    return "Unavailable";
}

function normalizeHealthState(status) {
    const batteryState = String(
        firstDefined(
            objectValue(
                status,
                "hardware",
                "battery",
                "state",
            ),
            "unknown",
        )
    ).toLowerCase();

    const temperatureState = String(
        firstDefined(
            objectValue(
                status,
                "system_health",
                "temperature",
                "state",
            ),
            "unknown",
        )
    ).toLowerCase();

    const visionAvailable = firstDefined(
        objectValue(
            status,
            "hardware",
            "vision",
            "service_available",
        ),
        false,
    );

    if (
        batteryState === "critical"
        || temperatureState === "critical"
    ) {
        return {
            label: "Needs Attention",
            cssClass: "status-critical",
        };
    }

    if (
        batteryState === "low"
        || temperatureState === "high"
        || visionAvailable === false
    ) {
        return {
            label: "Warning",
            cssClass: "status-warning",
        };
    }

    return {
        label: "Healthy",
        cssClass: "status-healthy",
    };
}


/* UI helpers */

function setHealthState(state) {
    const dot = element(
        "hud-health-dot"
    );

    dot.classList.remove(
        "status-unknown",
        "status-healthy",
        "status-warning",
        "status-critical",
    );

    dot.classList.add(
        state.cssClass
    );

    element(
        "hud-health"
    ).textContent = state.label;
}

function updateTimestamp() {
    element(
        "hud-updated"
    ).textContent = (
        `Updated ${
            new Date().toLocaleTimeString()
        }`
    );
}

function clearTimestamp() {
    element(
        "hud-updated"
    ).textContent =
        "Could not retrieve platform status.";
}


/* Rendering */

function renderStatus(status) {
    const hostname = firstDefined(
        status.hostname,
        objectValue(
            status,
            "identity",
            "hostname",
        ),
        "Betabox",
    );

    const addresses = firstDefined(
        status.ip_addresses,
        objectValue(
            status,
            "identity",
            "ip_addresses",
        ),
        [],
    );

    const ipAddress = (
        Array.isArray(addresses)
            ? addresses.find(
                (address) => (
                    !String(address).includes(":")
                )
            )
            : addresses
    );

    const batteryVoltage = firstDefined(
        objectValue(
            status,
            "hardware",
            "battery",
            "voltage",
        ),
    );

    const temperature = firstDefined(
        objectValue(
            status,
            "system_health",
            "temperature",
            "celsius",
        ),
    );

    const memoryPercent = firstDefined(
        objectValue(
            status,
            "system_health",
            "memory",
            "used_percent",
        ),
    );

    const diskPercent = firstDefined(
        objectValue(
            status,
            "system_health",
            "disk",
            "used_percent",
        ),
    );

    const visionText = visionLabel(
        status,
    );

    const batteryText = formatVoltage(
        batteryVoltage
    );

    const temperatureText = (
        formatTemperature(
            temperature
        )
    );

    const controlText = controlLabel(
        status
    );

    const networkText = networkLabel(
        status
    );

    const jupyterText = jupyterLabel(
        status
    );


    element(
        "hud-hostname"
    ).textContent = hostname;

    element(
        "hud-ip"
    ).textContent = ipAddress || "";

    element(
        "hud-battery"
    ).textContent = batteryText;

    element(
        "hud-control"
    ).textContent = controlText;

    element(
        "hud-vision"
    ).textContent = visionText;

    element(
        "detail-battery"
    ).textContent = batteryText;

    element(
        "detail-temperature"
    ).textContent = temperatureText;

    element(
        "detail-control"
    ).textContent = controlText;

    element(
        "detail-network"
    ).textContent = networkText;

    element(
        "detail-jupyter"
    ).textContent = jupyterText;

    element(
        "detail-memory"
    ).textContent = formatPercent(
        memoryPercent
    );

    element(
        "detail-disk"
    ).textContent = formatPercent(
        diskPercent
    );

    element(
        "detail-vision"
    ).textContent = visionText;

    setHealthState(
        normalizeHealthState(status)
    );

    updateTimestamp();
}

function renderDisconnected() {
    setHealthState(
        {
            label: "Disconnected",
            cssClass: "status-critical",
        }
    );

    element(
        "hud-battery"
    ).textContent = "--";

    element(
        "hud-control"
    ).textContent = "Unknown";

    element(
        "hud-vision"
    ).textContent = "Unknown";

    element(
        "detail-battery"
    ).textContent = "--";

    element(
        "detail-temperature"
    ).textContent = "--";

    element(
        "detail-control"
    ).textContent = "Unknown";

    element(
        "detail-network"
    ).textContent = "Unknown";

    element(
        "detail-jupyter"
    ).textContent = "Unknown";

    element(
        "detail-memory"
    ).textContent = "--";

    element(
        "detail-disk"
    ).textContent = "--";

    element(
        "detail-vision"
    ).textContent = "Unknown";

    clearTimestamp();
}


/* API */

async function loadStatus() {
    if (requestInProgress) {
        return;
    }

    requestInProgress = true;

    try {
        const response = await fetch(
            "/api/status",
            {
                cache: "no-store",
                headers: {
                    Accept: "application/json",
                },
            }
        );

        if (!response.ok) {
            throw new Error(
                "Status request failed: "
                + response.status
            );
        }

        const status = (
            await response.json()
        );

        renderStatus(
            status
        );

    } catch (error) {
        console.error(
            error
        );

        renderDisconnected();
    } finally {
        requestInProgress = false;
    }
}


/* UI */

function configureHudToggle() {
    const button = element(
        "hud-toggle"
    );

    const details = element(
        "hud-details"
    );

    button.addEventListener(
        "click",
        () => {
            const expanded = (
                button.getAttribute(
                    "aria-expanded"
                ) === "true"
            );

            button.setAttribute(
                "aria-expanded",
                String(!expanded),
            );

            details.hidden = expanded;
        },
    );
}


/* Refresh lifecycle */

function startAutomaticRefresh() {
    stopAutomaticRefresh();

    refreshTimer = window.setInterval(
        () => {
            void loadStatus();
        },
        STATUS_REFRESH_INTERVAL_MS
    );
}

function stopAutomaticRefresh() {
    if (refreshTimer === null) {
        return;
    }

    window.clearInterval(
        refreshTimer
    );

    refreshTimer = null;
}


/* Initialization */

function initializeHomePage() {
    configureHudToggle();

    startAutomaticRefresh();

    void loadStatus();
}


/* Event listeners */

if (
    document.readyState === "loading"
) {
    document.addEventListener(
        "DOMContentLoaded",
        initializeHomePage
    );
} else {
    initializeHomePage();
}

document.addEventListener(
    "visibilitychange",
    () => {
        if (document.hidden) {
            stopAutomaticRefresh();
            return;
        }

        startAutomaticRefresh();
        void loadStatus();
    }
);

window.addEventListener(
    "beforeunload",
    stopAutomaticRefresh
);
