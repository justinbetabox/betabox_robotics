"use strict";

const STATUS_INTERVAL_MS = 5000;

const element = (id) => document.getElementById(id);

function objectValue(object, ...path) {
    let current = object;

    for (const key of path) {
        if (
            current === null ||
            current === undefined ||
            typeof current !== "object"
        ) {
            return undefined;
        }

        current = current[key];
    }

    return current;
}

function firstDefined(...values) {
    return values.find(
        (value) => value !== undefined && value !== null
    );
}

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

function availabilityLabel(available, healthyText = "Ready") {
    if (available === true) {
        return healthyText;
    }

    if (available === false) {
        return "Offline";
    }

    return "--";
}

function normalizeHealthState(status) {
    const batteryState = String(
        firstDefined(
            objectValue(status, "hardware", "battery", "state"),
            "unknown"
        )
    ).toLowerCase();

    const temperatureState = String(
        firstDefined(
            objectValue(
                status,
                "system_health",
                "temperature",
                "state"
            ),
            "unknown"
        )
    ).toLowerCase();

    const visionAvailable = firstDefined(
        objectValue(
            status,
            "hardware",
            "vision",
            "service_available"
        ),
        false
    );

    const robotAvailable = firstDefined(
        objectValue(status, "hardware", "robot_available"),
        false
    );

    if (
        batteryState === "critical" ||
        temperatureState === "critical" ||
        robotAvailable === false
    ) {
        return {
            label: "Needs Attention",
            cssClass: "status-critical",
        };
    }

    if (
        batteryState === "low" ||
        temperatureState === "high" ||
        visionAvailable === false
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

function setHealthState(state) {
    const dot = element("hud-health-dot");

    dot.classList.remove(
        "status-unknown",
        "status-healthy",
        "status-warning",
        "status-critical"
    );

    dot.classList.add(state.cssClass);
    element("hud-health").textContent = state.label;
}

function renderStatus(status) {
    const hostname = firstDefined(
        status.hostname,
        objectValue(status, "identity", "hostname"),
        "Betabox"
    );

    const addresses = firstDefined(
        status.ip_addresses,
        objectValue(status, "identity", "ip_addresses"),
        []
    );

    const ipAddress = Array.isArray(addresses)
        ? addresses.find((address) => !String(address).includes(":"))
        : addresses;

    const batteryVoltage = firstDefined(
        objectValue(status, "hardware", "battery", "voltage")
    );

    const temperature = firstDefined(
        objectValue(
            status,
            "system_health",
            "temperature",
            "celsius"
        )
    );

    const memoryPercent = firstDefined(
        objectValue(
            status,
            "system_health",
            "memory",
            "used_percent"
        )
    );

    const diskPercent = firstDefined(
        objectValue(
            status,
            "system_health",
            "disk",
            "used_percent"
        )
    );

    const cameraRunning = firstDefined(
        objectValue(
            status,
            "hardware",
            "vision",
            "camera_running"
        ),
        false
    );

    const visionRunning = firstDefined(
        objectValue(status, "hardware", "vision", "running"),
        false
    );

    const audioAvailable = firstDefined(
        objectValue(status, "hardware", "audio", "available"),
        false
    );

    const i2cAvailable = firstDefined(
        objectValue(status, "hardware", "i2c", "available"),
        false
    );

    element("hud-hostname").textContent = hostname;
    element("hud-ip").textContent = ipAddress || "";

    const batteryText = formatVoltage(batteryVoltage);
    const temperatureText = formatTemperature(temperature);

    element("hud-battery").textContent = batteryText;
    element("hud-temperature").textContent = temperatureText;
    element("hud-camera").textContent = availabilityLabel(
        cameraRunning,
        "Ready"
    );

    element("detail-battery").textContent = batteryText;
    element("detail-temperature").textContent = temperatureText;
    element("detail-memory").textContent = formatPercent(memoryPercent);
    element("detail-disk").textContent = formatPercent(diskPercent);
    element("detail-camera").textContent =
        availabilityLabel(cameraRunning);
    element("detail-vision").textContent =
        availabilityLabel(visionRunning);
    element("detail-audio").textContent =
        availabilityLabel(audioAvailable);
    element("detail-i2c").textContent =
        availabilityLabel(i2cAvailable);

    setHealthState(normalizeHealthState(status));

    element("hud-updated").textContent =
        `Updated ${new Date().toLocaleTimeString()}`;
}

function renderDisconnected() {
    setHealthState({
        label: "Disconnected",
        cssClass: "status-critical",
    });

    element("hud-camera").textContent = "Unknown";
    element("hud-updated").textContent =
        "Could not retrieve platform status.";
}

async function refreshStatus() {
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
                `Status request failed: ${response.status}`
            );
        }

        const status = await response.json();
        renderStatus(status);
    } catch (error) {
        console.error(error);
        renderDisconnected();
    }
}

function configureHudToggle() {
    const button = element("hud-toggle");
    const details = element("hud-details");

    button.addEventListener("click", () => {
        const expanded =
            button.getAttribute("aria-expanded") === "true";

        button.setAttribute(
            "aria-expanded",
            String(!expanded)
        );

        details.hidden = expanded;
    });
}

document.addEventListener("DOMContentLoaded", () => {
    configureHudToggle();
    refreshStatus();

    window.setInterval(
        refreshStatus,
        STATUS_INTERVAL_MS
    );
});
