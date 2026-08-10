"use strict";

import { STATUS_API_URL } from "./constants.js";

import { elements } from "./dom.js";

import {
    determineHealth,
    formatTemperature,
    formatVoltage,
} from "./helpers.js";

function setHudHealth(label, cssClass) {
    elements.health.textContent = label;

    elements.healthDot.classList.remove(
        "hud-unknown",
        "hud-healthy",
        "hud-warning",
        "hud-critical",
    );

    elements.healthDot.classList.add(cssClass);
}

function validateStatusPayload(payload) {
    if (
        payload === null ||
        typeof payload !== "object" ||
        Array.isArray(payload)
    ) {
        throw new Error("Status API returned an invalid response.");
    }

    return payload;
}

async function responseErrorMessage(response) {
    let message = `Status request failed: HTTP ${response.status}`;

    try {
        const payload = await response.json();

        if (
            payload !== null &&
            typeof payload === "object" &&
            !Array.isArray(payload) &&
            typeof payload.message === "string" &&
            payload.message.trim() !== ""
        ) {
            message = payload.message.trim();
        }
    } catch (error) {
        console.debug("Unable to parse Status API error response:", error);
    }

    return message;
}

async function requestPlatformStatus() {
    const response = await fetch(STATUS_API_URL, {
        method: "GET",
        headers: {
            Accept: "application/json",
        },
        cache: "no-store",
    });

    if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
    }

    const payload = await response.json();

    return validateStatusPayload(payload);
}

function renderPlatformStatus(status) {
    const health = determineHealth(status);

    setHudHealth(health.label, health.cssClass);

    elements.battery.textContent = formatVoltage(
        status.hardware?.battery?.voltage,
    );

    elements.temperature.textContent = formatTemperature(
        status.system_health?.temperature?.celsius,
    );
}

function renderPlatformStatusError() {
    setHudHealth("Unavailable", "hud-critical");

    elements.battery.textContent = "--";

    elements.temperature.textContent = "--";
}

export async function refreshPlatformStatus() {
    try {
        const status = await requestPlatformStatus();

        renderPlatformStatus(status);
    } catch (error) {
        console.error("Could not load platform status:", error);

        renderPlatformStatusError();
    }
}
