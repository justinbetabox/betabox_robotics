"use strict";

import { EVENTS_API_URL } from "./constants.js";

import { elements } from "./dom.js";

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

function validatePayload(payload) {
    if (
        payload === null ||
        typeof payload !== "object" ||
        Array.isArray(payload)
    ) {
        throw new Error("The Events API returned an invalid response.");
    }

    if (
        payload.summary === null ||
        typeof payload.summary !== "object" ||
        Array.isArray(payload.summary)
    ) {
        throw new Error("The event response does not include a summary.");
    }

    if (!Array.isArray(payload.events)) {
        throw new Error("The event response does not include events.");
    }

    if (
        payload.components !== undefined &&
        !Array.isArray(payload.components)
    ) {
        throw new Error("The event response contains invalid components.");
    }

    return payload;
}

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

    const payload = await response.json();

    return validatePayload(payload);
}
