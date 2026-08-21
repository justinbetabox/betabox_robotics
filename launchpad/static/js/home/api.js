"use strict";

import { STATUS_API_URL } from "./constants.js";

function validateStatusPayload(payload) {
    if (
        payload === null ||
        typeof payload !== "object" ||
        Array.isArray(payload)
    ) {
        throw new Error("The Status API returned an invalid response.");
    }

    if (
        payload.hardware !== undefined &&
        (payload.hardware === null ||
            typeof payload.hardware !== "object" ||
            Array.isArray(payload.hardware))
    ) {
        throw new Error(
            "The Status API returned invalid hardware information.",
        );
    }

    if (
        payload.system_health !== undefined &&
        (payload.system_health === null ||
            typeof payload.system_health !== "object" ||
            Array.isArray(payload.system_health))
    ) {
        throw new Error(
            "The Status API returned invalid system health information.",
        );
    }

    if (
        payload.overall_health !== undefined &&
        (payload.overall_health === null ||
            typeof payload.overall_health !== "object" ||
            Array.isArray(payload.overall_health))
    ) {
        throw new Error(
            "The Status API returned invalid overall health information.",
        );
    }

    return payload;
}

async function responseErrorMessage(response) {
    let message = `Status API returned HTTP ${response.status}.`;

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

export async function requestStatus() {
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
