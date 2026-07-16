"use strict";

const STATUS_API_URL = "/api/status";
const AUTO_REFRESH_INTERVAL_MS = 30_000;

const SERVICE_LABELS = {
    "set-hostname-from-serial.service":
        "Robot Hostname",
    "betabox-boot-announce.service":
        "Boot Announcer",
    "betabox-monitor.service":
        "Health Monitor",
    "jupyterhub.service":
        "JupyterHub",
    "betabox-video.service":
        "Video Service",
    "wifi-fallback.service":
        "Wi-Fi Fallback",
    "betabox-launchpad.service":
        "Launchpad",
};

let requestInProgress = false;
let refreshTimer = null;


/*
 * Basic helpers
 */

function getElement(id) {
    return document.getElementById(id);
}


function setText(id, value) {
    const element = getElement(id);

    if (element) {
        element.textContent = value;
    }
}


function formatBoolean(value) {
    return value ? "Yes" : "No";
}


function formatState(value) {
    if (
        value === null
        || value === undefined
        || value === ""
    ) {
        return "Unavailable";
    }

    return String(value)
        .replace(/[_-]+/g, " ")
        .replace(
            /\b\w/g,
            (letter) => letter.toUpperCase(),
        );
}


function formatVoltage(value) {
    if (typeof value !== "number") {
        return "Unavailable";
    }

    return `${value.toFixed(2)} V`;
}


function formatTemperature(value) {
    if (typeof value !== "number") {
        return "Unavailable";
    }

    return `${value.toFixed(1)} °C`;
}


function formatPercent(value) {
    if (typeof value !== "number") {
        return "Unavailable";
    }

    return `${value.toFixed(1)}%`;
}


function formatMegabytes(value) {
    if (typeof value !== "number") {
        return "Unavailable";
    }

    return `${value} MB`;
}


function formatGigabytes(value) {
    if (typeof value !== "number") {
        return "Unavailable";
    }

    return `${value.toFixed(1)} GB`;
}


function serviceDisplayName(name) {
    return SERVICE_LABELS[name] ?? name;
}


/*
 * Status classification
 */

function statusClass(state) {
    const normalized = String(state ?? "")
        .trim()
        .toLowerCase();

    if (
        [
            "ok",
            "normal",
            "healthy",
            "active",
            "available",
            "connected",
            "running",
            "responding",
            "ready",
        ].includes(normalized)
    ) {
        return "healthy";
    }

    if (
        [
            "warning",
            "degraded",
            "low",
            "unknown",
            "disconnected",
            "partial",
        ].includes(normalized)
    ) {
        return "warning";
    }

    if (
        [
            "critical",
            "failed",
            "inactive",
            "unavailable",
            "error",
            "stopped",
        ].includes(normalized)
    ) {
        return "critical";
    }

    return "unknown";
}


function setOverallStatus(label, state) {
    setText(
        "overall-status",
        label,
    );

    const indicator = getElement(
        "overall-indicator",
    );

    if (!indicator) {
        return;
    }

    indicator.classList.remove(
        "status-healthy",
        "status-warning",
        "status-critical",
        "status-unknown",
    );

    indicator.classList.add(
        `status-${statusClass(state)}`,
    );
}


function determineOverallStatus(data) {
    const serviceStates = Object.values(
        data.services ?? {},
    );

    const failedServices = serviceStates.filter(
        (state) => state === "failed",
    );

    const batteryState = (
        data.hardware?.battery?.state
    );

    const temperatureState = (
        data.system_health?.temperature?.state
    );

    const memoryState = (
        data.system_health?.memory?.state
    );

    const diskState = (
        data.system_health?.disk?.state
    );

    const throttling = (
        data.system_health?.throttling ?? {}
    );

    if (
        batteryState === "critical"
        || temperatureState === "critical"
        || memoryState === "critical"
        || diskState === "critical"
        || throttling.undervoltage_now
    ) {
        return {
            label: "Critical",
            state: "critical",
        };
    }

    if (
        failedServices.length > 0
        || batteryState === "low"
        || temperatureState === "warning"
        || memoryState === "warning"
        || diskState === "warning"
        || throttling.throttled_now
    ) {
        return {
            label: "Needs Attention",
            state: "warning",
        };
    }

    return {
        label: "Healthy",
        state: "healthy",
    };
}


/*
 * Generic detail cards
 */

function createDetailItem(label, value) {
    const item = document.createElement(
        "article",
    );

    item.className = "detail-item";

    const labelElement = document.createElement(
        "span",
    );

    labelElement.className = "detail-label";
    labelElement.textContent = label;

    const valueElement = document.createElement(
        "strong",
    );

    valueElement.className = "detail-value";
    valueElement.textContent = value;

    item.append(
        labelElement,
        valueElement,
    );

    return item;
}


function renderDetailItems(
    containerId,
    items,
) {
    const container = getElement(containerId);

    if (!container) {
        return;
    }

    container.replaceChildren();

    for (const [label, value] of items) {
        container.append(
            createDetailItem(
                label,
                value,
            ),
        );
    }
}


/*
 * Overview
 */

function renderOverview(data) {
    const overall = determineOverallStatus(
        data,
    );

    setOverallStatus(
        overall.label,
        overall.state,
    );

    const control = data.control ?? {};

    const battery = (
        data.hardware?.battery ?? {}
    );

    const vision = (
        data.hardware?.vision ?? {}
    );

    const temperature = (
        data.system_health?.temperature ?? {}
    );

    const jupyterhub = (
        data.jupyterhub ?? {}
    );

    setText(
        "battery-status",
        formatVoltage(battery.voltage),
    );

    setText(
        "temperature-status",
        formatTemperature(
            temperature.celsius,
        ),
    );

    setText(
        "robot-status",
        control.available
            ? "Available"
            : "Unavailable",
    );

    setText(
        "vision-status",
        vision.camera_running
            && vision.camera_has_frame
            ? "Online"
            : vision.running
                ? "Starting"
                : "Offline",
    );

    setText(
        "audio-status",
        jupyterhub.responding
            ? "Online"
            : "Offline",
    );

    renderServiceSummary(data);
}


/*
 * Attention section
 */

function createAttentionItem(
    title,
    message,
    severity,
) {
    const item = document.createElement(
        "article",
    );

    item.className = (
        `attention-item attention-${severity}`
    );

    const indicator = document.createElement(
        "span",
    );

    indicator.className = (
        `status-indicator status-${severity}`
    );

    indicator.setAttribute(
        "aria-hidden",
        "true",
    );

    const text = document.createElement(
        "div",
    );

    const heading = document.createElement(
        "h3",
    );

    heading.textContent = title;

    const description = document.createElement(
        "p",
    );

    description.textContent = message;

    text.append(
        heading,
        description,
    );

    item.append(
        indicator,
        text,
    );

    return item;
}


function collectAttentionItems(data) {
    const items = [];

    for (
        const [service, state]
        of Object.entries(data.services ?? {})
    ) {
        if (state === "failed") {
            items.push({
                title: serviceDisplayName(service),
                message: (
                    `${service} has failed.`
                ),
                severity: "critical",
            });

            continue;
        }

        if (
            state !== "active"
            && state !== "inactive"
        ) {
            items.push({
                title: serviceDisplayName(service),
                message: (
                    `${service} reported `
                    + `${formatState(state)}.`
                ),
                severity: "warning",
            });
        }
    }

    const battery = (
        data.hardware?.battery ?? {}
    );

    if (battery.state === "critical") {
        items.push({
            title: "Battery Critical",
            message: (
                `Battery voltage is `
                + `${formatVoltage(battery.voltage)}.`
            ),
            severity: "critical",
        });
    } else if (battery.state === "low") {
        items.push({
            title: "Battery Low",
            message: (
                `Battery voltage is `
                + `${formatVoltage(battery.voltage)}.`
            ),
            severity: "warning",
        });
    }

    if (battery.error) {
        items.push({
            title: "Battery Reading Error",
            message: String(battery.error),
            severity: "warning",
        });
    }

    const vision = (
        data.hardware?.vision ?? {}
    );

    if (!vision.service_available) {
        items.push({
            title: "Video Service Unavailable",
            message: (
                "The robot video service could not "
                + "be reached."
            ),
            severity: "critical",
        });
    } else if (
        !vision.camera_running
        || !vision.camera_has_frame
    ) {
        items.push({
            title: "Camera Not Ready",
            message: (
                "The video service is available, "
                + "but the camera is not producing "
                + "a usable frame."
            ),
            severity: "warning",
        });
    }

    if (vision.error) {
        items.push({
            title: "Camera Error",
            message: String(vision.error),
            severity: "warning",
        });
    }

    const temperature = (
        data.system_health?.temperature ?? {}
    );

    if (temperature.state === "critical") {
        items.push({
            title: "CPU Temperature Critical",
            message: (
                `Current temperature is `
                + `${formatTemperature(
                    temperature.celsius,
                )}.`
            ),
            severity: "critical",
        });
    } else if (
        temperature.state === "warning"
    ) {
        items.push({
            title: "CPU Temperature High",
            message: (
                `Current temperature is `
                + `${formatTemperature(
                    temperature.celsius,
                )}.`
            ),
            severity: "warning",
        });
    }

    const memory = (
        data.system_health?.memory ?? {}
    );

    if (memory.state === "critical") {
        items.push({
            title: "Memory Critical",
            message: (
                `${formatPercent(
                    memory.used_percent,
                )} of memory is in use.`
            ),
            severity: "critical",
        });
    } else if (
        memory.state === "warning"
    ) {
        items.push({
            title: "Memory Usage High",
            message: (
                `${formatPercent(
                    memory.used_percent,
                )} of memory is in use.`
            ),
            severity: "warning",
        });
    }

    const disk = (
        data.system_health?.disk ?? {}
    );

    if (disk.state === "critical") {
        items.push({
            title: "Disk Space Critical",
            message: (
                `${formatPercent(
                    disk.used_percent,
                )} of the disk is in use.`
            ),
            severity: "critical",
        });
    } else if (
        disk.state === "warning"
    ) {
        items.push({
            title: "Disk Usage High",
            message: (
                `${formatPercent(
                    disk.used_percent,
                )} of the disk is in use.`
            ),
            severity: "warning",
        });
    }

    const throttling = (
        data.system_health?.throttling ?? {}
    );

    if (throttling.undervoltage_now) {
        items.push({
            title: "Undervoltage Detected",
            message: (
                "The Raspberry Pi is currently "
                + "receiving insufficient power."
            ),
            severity: "critical",
        });
    }

    if (throttling.throttled_now) {
        items.push({
            title: "CPU Throttling",
            message: (
                "The Raspberry Pi is currently "
                + "reducing performance."
            ),
            severity: "warning",
        });
    }

    if (
        throttling.undervoltage_occurred
        && !throttling.undervoltage_now
    ) {
        items.push({
            title: "Previous Undervoltage",
            message: (
                "The Raspberry Pi detected an "
                + "undervoltage condition since boot."
            ),
            severity: "warning",
        });
    }

    if (
        throttling.throttled_occurred
        && !throttling.throttled_now
    ) {
        items.push({
            title: "Previous CPU Throttling",
            message: (
                "The Raspberry Pi was throttled "
                + "at least once since boot."
            ),
            severity: "warning",
        });
    }

    if (
        data.jupyterhub?.active
        && !data.jupyterhub?.responding
    ) {
        items.push({
            title: "JupyterHub Not Responding",
            message: (
                data.jupyterhub?.message
                ?? "The service is active but its "
                + "HTTP endpoint is unavailable."
            ),
            severity: "warning",
        });
    }

    return items;
}


function renderAttention(data) {
    const section = getElement(
        "attention-section",
    );

    const container = getElement(
        "attention-list",
    );

    if (!section || !container) {
        return;
    }

    const items = collectAttentionItems(
        data,
    );

    container.replaceChildren();

    if (items.length === 0) {
        section.hidden = true;
        return;
    }

    for (const item of items) {
        container.append(
            createAttentionItem(
                item.title,
                item.message,
                item.severity,
            ),
        );
    }

    section.hidden = false;
}


/*
 * Hardware and control
 */

function renderHardware(data) {
    const battery = (
        data.hardware?.battery ?? {}
    );

    const vision = (
        data.hardware?.vision ?? {}
    );

    const control = data.control ?? {};

    let controlOwner = "None";

    if (control.owner) {
        controlOwner = String(control.owner);
    }

    renderDetailItems(
        "hardware-status",
        [
            [
                "Battery Voltage",
                formatVoltage(battery.voltage),
            ],
            [
                "Battery State",
                formatState(battery.state),
            ],
            [
                "Battery Available",
                formatBoolean(
                    Boolean(battery.available),
                ),
            ],
            [
                "Control Available",
                formatBoolean(
                    Boolean(control.available),
                ),
            ],
            [
                "Control Owner",
                controlOwner,
            ],
            [
                "Camera Service",
                vision.service_available
                    ? "Available"
                    : "Unavailable",
            ],
            [
                "Camera Running",
                formatBoolean(
                    Boolean(vision.camera_running),
                ),
            ],
            [
                "Camera Has Frame",
                formatBoolean(
                    Boolean(vision.camera_has_frame),
                ),
            ],
            [
                "Video Clients",
                String(vision.clients ?? 0),
            ],
        ],
    );
}


/*
 * System resources
 */

function renderSystem(data) {
    const health = data.system_health ?? {};

    const temperature = (
        health.temperature ?? {}
    );

    const throttling = (
        health.throttling ?? {}
    );

    const memory = (
        health.memory ?? {}
    );

    const disk = (
        health.disk ?? {}
    );

    renderDetailItems(
        "system-status",
        [
            [
                "Platform Version",
                data.version ?? "Unavailable",
            ],
            [
                "Hostname",
                data.hostname ?? "Unavailable",
            ],
            [
                "CPU Temperature",
                formatTemperature(
                    temperature.celsius,
                ),
            ],
            [
                "Temperature State",
                formatState(
                    temperature.state,
                ),
            ],
            [
                "Memory Used",
                formatPercent(
                    memory.used_percent,
                ),
            ],
            [
                "Memory Available",
                formatMegabytes(
                    memory.available_mb,
                ),
            ],
            [
                "Memory Total",
                formatMegabytes(
                    memory.total_mb,
                ),
            ],
            [
                "Disk Used",
                formatPercent(
                    disk.used_percent,
                ),
            ],
            [
                "Disk Free",
                formatGigabytes(
                    disk.free_gb,
                ),
            ],
            [
                "Disk Total",
                formatGigabytes(
                    disk.total_gb,
                ),
            ],
            [
                "Undervoltage Now",
                throttling.undervoltage_now
                    ? "Detected"
                    : "No",
            ],
            [
                "Undervoltage Since Boot",
                throttling.undervoltage_occurred
                    ? "Detected"
                    : "No",
            ],
            [
                "Throttled Now",
                throttling.throttled_now
                    ? "Yes"
                    : "No",
            ],
            [
                "Throttled Since Boot",
                throttling.throttled_occurred
                    ? "Yes"
                    : "No",
            ],
            [
                "Throttle Flags",
                throttling.raw
                    ?? "Unavailable",
            ],
        ],
    );
}


/*
 * Network
 */

function renderNetwork(data) {
    const health = data.system_health ?? {};

    const ethernet = (
        health.ethernet ?? {}
    );

    const wifi = (
        health.wifi ?? {}
    );

    renderDetailItems(
        "network-status",
        [
            [
                "IP Addresses",
                Array.isArray(data.ip_addresses)
                    && data.ip_addresses.length > 0
                    ? data.ip_addresses.join(", ")
                    : "Unavailable",
            ],
            [
                "Ethernet Interface",
                ethernet.name
                    ?? "Unavailable",
            ],
            [
                "Ethernet Connected",
                formatBoolean(
                    Boolean(ethernet.connected),
                ),
            ],
            [
                "Ethernet State",
                ethernet.state
                    ?? "Unavailable",
            ],
            [
                "Ethernet Connection",
                ethernet.connection
                    || "None",
            ],
            [
                "Wi-Fi Interface",
                wifi.name
                    ?? "Unavailable",
            ],
            [
                "Wi-Fi Connected",
                formatBoolean(
                    Boolean(wifi.connected),
                ),
            ],
            [
                "Wi-Fi State",
                wifi.state
                    ?? "Unavailable",
            ],
            [
                "Wi-Fi Connection",
                wifi.connection
                    || "None",
            ],
        ],
    );
}


/*
 * Page state
 */

function updateTimestamp() {
    setText(
        "status-updated",
        `Updated ${new Date().toLocaleString()}`,
    );
}


function setConnectionState(
    state,
    text,
) {
    const element = getElement(
        "status-connection",
    );

    if (!element) {
        return;
    }

    element.classList.remove(
        "status-connecting",
        "status-connected",
        "status-error",
    );

    element.classList.add(
        `status-${state}`,
    );

    element.textContent = text;
}


function showError(message) {
    const panel = getElement(
        "status-error-panel",
    );

    setText(
        "status-error-message",
        message,
    );

    if (panel) {
        panel.hidden = false;
    }
}


function hideError() {
    const panel = getElement(
        "status-error-panel",
    );

    if (panel) {
        panel.hidden = true;
    }
}


/*
 * Full render
 */

function renderStatus(data) {
    renderOverview(data);
    renderAttention(data);
    renderHardware(data);
    renderSystem(data);
    renderNetwork(data);
    updateTimestamp();
}

function renderServiceSummary(data) {
    const states = Object.values(
        data.services ?? {},
    );

    const activeCount = states.filter(
        (state) => state === "active",
    ).length;

    const failedCount = states.filter(
        (state) => state === "failed",
    ).length;

    const otherCount = (
        states.length
        - activeCount
        - failedCount
    );

    const parts = [
        `${activeCount} active`,
    ];

    if (failedCount > 0) {
        parts.push(
            `${failedCount} failed`,
        );
    }

    if (otherCount > 0) {
        parts.push(
            `${otherCount} other`,
        );
    }

    setText(
        "services-status",
        parts.join(" · "),
    );
}

/*
 * API loading
 */

async function loadStatus() {
    if (requestInProgress) {
        return;
    }

    requestInProgress = true;

    const refreshButton = getElement(
        "refresh-status",
    );

    if (refreshButton) {
        refreshButton.disabled = true;
    }

    setConnectionState(
        "connecting",
        "Refreshing…",
    );

    try {
        const response = await fetch(
            STATUS_API_URL,
            {
                method: "GET",
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            },
        );

        if (!response.ok) {
            throw new Error(
                `Status API returned HTTP `
                + `${response.status}.`,
            );
        }

        const data = await response.json();

        if (
            !data
            || typeof data !== "object"
            || Array.isArray(data)
        ) {
            throw new Error(
                "Status API returned an "
                + "invalid response.",
            );
        }

        renderStatus(data);
        hideError();

        setConnectionState(
            "connected",
            "Live",
        );
    } catch (error) {
        console.error(
            "Unable to load platform status:",
            error,
        );

        showError(
            error instanceof Error
                ? error.message
                : "Unable to load platform status.",
        );

        setConnectionState(
            "error",
            "Disconnected",
        );
    } finally {
        requestInProgress = false;

        if (refreshButton) {
            refreshButton.disabled = false;
        }
    }
}


/*
 * Initialization
 */

function startAutomaticRefresh() {
    if (refreshTimer !== null) {
        window.clearInterval(
            refreshTimer,
        );
    }

    refreshTimer = window.setInterval(
        loadStatus,
        AUTO_REFRESH_INTERVAL_MS,
    );
}


function initialize() {
    getElement(
        "refresh-status",
    )?.addEventListener(
        "click",
        loadStatus,
    );

    getElement(
        "retry-status",
    )?.addEventListener(
        "click",
        loadStatus,
    );

    document.addEventListener(
        "visibilitychange",
        () => {
            if (
                document.visibilityState
                === "visible"
            ) {
                loadStatus();
            }
        },
    );

    startAutomaticRefresh();
    loadStatus();
}


document.addEventListener(
    "DOMContentLoaded",
    initialize,
);
