"use strict";

import { EVENTS_API_URL } from "./constants.js";

import { elements } from "./dom.js";

/* Request URL */

function buildApiUrl() {
    const params = new URLSearchParams();

    const severity = elements.severityFilter.value;

    const component = elements.componentFilter.value;

    const last = elements.limitFilter.value;

    if (severity !== "") {
        params.set("severity", severity);
    }

    if (component !== "") {
        params.set("component", component);
    }

    params.set("last", last);

    return `${EVENTS_API_URL}?${params}`;
}

/* Validation */

function normalizeCount(value) {
    const number = Number(value);

    if (!Number.isFinite(number) || number < 0) {
        return 0;
    }

    return Math.floor(number);
}

function normalizeSummary(summary) {
    if (
        summary === null ||
        typeof summary !== "object" ||
        Array.isArray(summary)
    ) {
        throw new Error("The event response does not include a summary.");
    }

    return {
        ...summary,

        total: normalizeCount(summary.total),

        total_available: normalizeCount(summary.total_available),

        info: normalizeCount(summary.info),

        warning: normalizeCount(summary.warning),

        error: normalizeCount(summary.error),

        critical: normalizeCount(summary.critical),
    };
}

function normalizeSeverity(value) {
    switch (value) {
        case "info":
        case "warning":
        case "error":
        case "critical":
            return value;

        default:
            return "info";
    }
}

function normalizeEvent(event) {
    if (event === null || typeof event !== "object" || Array.isArray(event)) {
        throw new Error("The event response contains an invalid event.");
    }

    return {
        ...event,

        severity: normalizeSeverity(event.severity),

        component:
            typeof event.component === "string" && event.component.trim() !== ""
                ? event.component.trim()
                : "unknown",

        message:
            typeof event.message === "string" && event.message.trim() !== ""
                ? event.message.trim()
                : "Unknown event",

        timestamp: typeof event.timestamp === "string" ? event.timestamp : "",

        event: typeof event.event === "string" ? event.event : "",

        details:
            event.details !== null &&
            typeof event.details === "object" &&
            !Array.isArray(event.details)
                ? event.details
                : null,
    };
}

function normalizeComponents(components) {
    if (components === undefined) {
        return [];
    }

    if (!Array.isArray(components)) {
        throw new Error("The event response contains invalid components.");
    }

    const values = components
        .filter((component) => typeof component === "string")
        .map((component) => component.trim())
        .filter((component) => component !== "");

    return [...new Set(values)].sort((left, right) =>
        left.localeCompare(right, undefined, {
            sensitivity: "base",
        }),
    );
}

function validatePayload(payload) {
    if (
        payload === null ||
        typeof payload !== "object" ||
        Array.isArray(payload)
    ) {
        throw new Error("The Events API returned an invalid response.");
    }

    if (!Array.isArray(payload.events)) {
        throw new Error("The event response does not include events.");
    }

    return {
        ...payload,

        summary: normalizeSummary(payload.summary),

        events: payload.events.map(normalizeEvent),

        components: normalizeComponents(payload.components),
    };
}

/* Error responses */

async function responseErrorMessage(response) {
    let message = `Events API returned HTTP ${response.status}.`;

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
        console.debug("Unable to parse Events API error response:", error);
    }

    return message;
}

/* API */

export async function requestEvents() {
    const response = await fetch(buildApiUrl(), {
        method: "GET",
        headers: {
            Accept: "application/json",
        },
        cache: "no-store",
    });

    if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
    }

    return validatePayload(await response.json());
}
