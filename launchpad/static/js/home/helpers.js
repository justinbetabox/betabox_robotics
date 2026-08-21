"use strict";

/* Data helpers */

export function objectValue(object, ...path) {
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

export function firstDefined(...values) {
    return values.find((value) => value !== undefined && value !== null);
}

/* Formatting */

export function formatVoltage(value) {
    const voltage = Number(value);

    if (!Number.isFinite(voltage)) {
        return "--";
    }

    return `${voltage.toFixed(2)} V`;
}

export function formatTemperature(value) {
    const temperature = Number(value);

    if (!Number.isFinite(temperature)) {
        return "--";
    }

    return `${temperature.toFixed(1)} °C`;
}

export function formatPercent(value) {
    const percent = Number(value);

    if (!Number.isFinite(percent)) {
        return "--";
    }

    return `${percent.toFixed(0)}%`;
}

/* Classification */

export function controlLabel(status) {
    const runtime = objectValue(status, "runtime") ?? {};

    if (
        runtime.ready !== true ||
        runtime.ownership_acquired !== true ||
        runtime.hardware_initialized !== true
    ) {
        return "Unavailable";
    }

    if (!runtime.control_owner) {
        return "Available";
    }

    const owner = String(runtime.control_owner);
    const normalized = owner.toLowerCase();

    if (normalized.includes("manual drive")) {
        return "Manual Drive";
    }

    if (normalized.includes("python")) {
        return "Python App";
    }

    return owner;
}

export function visionLabel(status) {
    const vision = objectValue(status, "hardware", "vision") ?? {};

    if (vision.service_available !== true) {
        return "Unavailable";
    }

    if (vision.camera_running === true && vision.camera_has_frame === true) {
        return "Ready";
    }

    if (vision.running === true || vision.camera_running === true) {
        return "Starting";
    }

    return "Offline";
}

export function networkLabel(status) {
    const ethernetConnected = firstDefined(
        objectValue(status, "system_health", "ethernet", "connected"),
        false,
    );

    const wifiConnected = firstDefined(
        objectValue(status, "system_health", "wifi", "connected"),
        false,
    );

    if (ethernetConnected === true) {
        return "Ethernet";
    }

    if (wifiConnected === true) {
        return "Wi-Fi";
    }

    return "Disconnected";
}

export function jupyterLabel(status) {
    const active = firstDefined(
        objectValue(status, "jupyterhub", "active"),
        false,
    );

    const responding = firstDefined(
        objectValue(status, "jupyterhub", "responding"),
        false,
    );

    const state = String(
        firstDefined(objectValue(status, "jupyterhub", "state"), "unknown"),
    ).toLowerCase();

    if (active === true && responding === true) {
        return "Ready";
    }

    if (state === "activating" || state === "reloading") {
        return "Starting";
    }

    return "Unavailable";
}

export function normalizeHealthState(status) {
    const health = objectValue(status, "overall_health");

    if (
        health === null ||
        health === undefined ||
        typeof health !== "object" ||
        Array.isArray(health)
    ) {
        return {
            label: "Unknown",
            cssClass: "status-unknown",
        };
    }

    switch (health.state) {
        case "healthy":
            return {
                label: "Healthy",
                cssClass: "status-healthy",
            };

        case "warning":
            return {
                label: "Warning",
                cssClass: "status-warning",
            };

        case "error":
        case "critical":
            return {
                label: "Needs Attention",
                cssClass: "status-critical",
            };

        default:
            return {
                label: "Unknown",
                cssClass: "status-unknown",
            };
    }
}
