"use strict";

import { STATUS_API_URL } from "./constants.js";

/* Validation */

function validatePayload(data) {
    if (data === null || typeof data !== "object" || Array.isArray(data)) {
        throw new Error("Status API returned an invalid response.");
    }

    return data;
}

/* Error handling */

async function errorMessage(response) {
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
        console.debug("Unable to parse status API error response:", error);
    }

    return message;
}

/* API */

export async function requestStatus() {
    const response = await fetch(STATUS_API_URL, {
        method: "GET",
        headers: {
            Accept: "application/json",
        },
        cache: "no-store",
    });

    if (!response.ok) {
        throw new Error(await errorMessage(response));
    }

    const data = await response.json();

    return validatePayload(data);
}
