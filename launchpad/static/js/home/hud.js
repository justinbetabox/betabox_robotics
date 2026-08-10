"use strict";

import { elements } from "./dom.js";

import {
    controlLabel,
    firstDefined,
    formatPercent,
    formatTemperature,
    formatVoltage,
    jupyterLabel,
    networkLabel,
    normalizeHealthState,
    objectValue,
    visionLabel,
} from "./helpers.js";

function setHealthState(state) {
    elements.healthDot.classList.remove(
        "status-unknown",
        "status-healthy",
        "status-warning",
        "status-critical",
    );

    elements.healthDot.classList.add(state.cssClass);

    elements.health.textContent = state.label;
}

function updateTimestamp() {
    elements.updated.textContent = `Updated ${new Date().toLocaleTimeString()}`;
}

function clearTimestamp() {
    elements.updated.textContent = "Could not retrieve platform status.";
}

export function renderStatus(status) {
    const hostname = firstDefined(
        status.hostname,
        objectValue(status, "identity", "hostname"),
        "Betabox",
    );

    const addresses = firstDefined(
        status.ip_addresses,
        objectValue(status, "identity", "ip_addresses"),
        [],
    );

    const ipAddress = Array.isArray(addresses)
        ? addresses.find((address) => !String(address).includes(":"))
        : addresses;

    const batteryVoltage = objectValue(
        status,
        "hardware",
        "battery",
        "voltage",
    );

    const temperature = objectValue(
        status,
        "system_health",
        "temperature",
        "celsius",
    );

    const memoryPercent = objectValue(
        status,
        "system_health",
        "memory",
        "used_percent",
    );

    const diskPercent = objectValue(
        status,
        "system_health",
        "disk",
        "used_percent",
    );

    const visionText = visionLabel(status);

    const batteryText = formatVoltage(batteryVoltage);

    const temperatureText = formatTemperature(temperature);

    const controlText = controlLabel(status);

    const networkText = networkLabel(status);

    const jupyterText = jupyterLabel(status);

    elements.hostname.textContent = String(hostname);

    elements.ip.textContent = ipAddress ? String(ipAddress) : "";

    elements.battery.textContent = batteryText;

    elements.control.textContent = controlText;

    elements.vision.textContent = visionText;

    elements.detailBattery.textContent = batteryText;

    elements.detailTemperature.textContent = temperatureText;

    elements.detailControl.textContent = controlText;

    elements.detailNetwork.textContent = networkText;

    elements.detailJupyter.textContent = jupyterText;

    elements.detailMemory.textContent = formatPercent(memoryPercent);

    elements.detailDisk.textContent = formatPercent(diskPercent);

    elements.detailVision.textContent = visionText;

    setHealthState(normalizeHealthState(status));

    updateTimestamp();
}

export function renderDisconnected() {
    setHealthState({
        label: "Disconnected",
        cssClass: "status-critical",
    });

    elements.battery.textContent = "--";

    elements.control.textContent = "Unknown";

    elements.vision.textContent = "Unknown";

    elements.detailBattery.textContent = "--";

    elements.detailTemperature.textContent = "--";

    elements.detailControl.textContent = "Unknown";

    elements.detailNetwork.textContent = "Unknown";

    elements.detailJupyter.textContent = "Unknown";

    elements.detailMemory.textContent = "--";

    elements.detailDisk.textContent = "--";

    elements.detailVision.textContent = "Unknown";

    clearTimestamp();
}

export function configureHudToggle() {
    elements.toggle.addEventListener("click", () => {
        const expanded =
            elements.toggle.getAttribute("aria-expanded") === "true";

        const nextExpanded = !expanded;

        elements.toggle.setAttribute("aria-expanded", String(nextExpanded));

        elements.details.hidden = !nextExpanded;
    });
}
