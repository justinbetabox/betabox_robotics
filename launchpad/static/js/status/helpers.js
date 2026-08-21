"use strict";

import { SERVICE_LABELS } from "./constants.js";

/* Formatting */

export function formatBoolean(value) {
    if (value === true) {
        return "Yes";
    }

    if (value === false) {
        return "No";
    }

    return "Unavailable";
}

export function formatState(value) {
    if (value === null || value === undefined || value === "") {
        return "Unavailable";
    }

    return String(value)
        .replace(/[_-]+/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatVoltage(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
        return "Unavailable";
    }

    return `${value.toFixed(2)} V`;
}

export function formatTemperature(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
        return "Unavailable";
    }

    return `${value.toFixed(1)} °C`;
}

export function formatPercent(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
        return "Unavailable";
    }

    return `${value.toFixed(1)}%`;
}

export function formatMegabytes(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
        return "Unavailable";
    }

    return `${value} MB`;
}

export function formatGigabytes(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
        return "Unavailable";
    }

    return `${value.toFixed(1)} GB`;
}

/* Classification */

export function serviceDisplayName(name) {
    if (typeof name !== "string" || name.trim() === "") {
        return "Unknown Service";
    }

    const nameValue = name.trim();

    return SERVICE_LABELS[nameValue] ?? nameValue;
}

export function visionLabel(vision) {
    if (
        vision === null ||
        typeof vision !== "object" ||
        Array.isArray(vision)
    ) {
        return "Unavailable";
    }

    if (!vision.service_available) {
        return "Unavailable";
    }

    if (vision.camera_running && vision.camera_has_frame) {
        return "Ready";
    }

    if (vision.running || vision.camera_running) {
        return "Starting";
    }

    return "Offline";
}

export function controlLabel(runtime) {
    if (
        runtime === null ||
        typeof runtime !== "object" ||
        Array.isArray(runtime)
    ) {
        return "Unavailable";
    }

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

export function statusClass(value) {
    const normalized = String(value ?? "")
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

/* Detail cards */

export function createDetailItem(label, value) {
    const item = document.createElement("article");

    item.className = "detail-card";

    const labelElement = document.createElement("span");

    labelElement.className = "detail-label";

    labelElement.textContent = String(label);

    const valueElement = document.createElement("strong");

    valueElement.className = "detail-value";

    valueElement.textContent = String(value);

    item.append(labelElement, valueElement);

    return item;
}

export function renderDetailItems(container, items) {
    if (!(container instanceof HTMLElement)) {
        throw new TypeError("container must be an HTMLElement");
    }

    if (!Array.isArray(items)) {
        throw new TypeError("items must be an array");
    }

    container.replaceChildren();

    for (const item of items) {
        if (!Array.isArray(item) || item.length !== 2) {
            throw new TypeError(
                "each detail item must contain a label and value",
            );
        }

        const [label, value] = item;

        container.append(createDetailItem(label, value));
    }
}

/* Time */

export function updateTimestamp(element) {
    if (!(element instanceof HTMLElement)) {
        throw new TypeError("element must be an HTMLElement");
    }

    element.textContent = `Last updated ${new Date().toLocaleString()}`;
}
