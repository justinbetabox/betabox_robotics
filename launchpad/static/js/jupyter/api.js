"use strict";

import { JUPYTER_STATUS_URL } from "./constants.js";

function validatePayload(data) {
    if (data === null || typeof data !== "object" || Array.isArray(data)) {
        throw new Error(
            "The Jupyter status API returned " + "an invalid response.",
        );
    }

    if (
        typeof data.active !== "boolean" ||
        typeof data.responding !== "boolean"
    ) {
        throw new Error(
            "The Jupyter status response is " +
                "missing availability information.",
        );
    }

    if (typeof data.state !== "string") {
        throw new Error(
            "The Jupyter status response is " + "missing its service state.",
        );
    }

    const port = Number(data.port);

    if (!Number.isInteger(port) || port < 1 || port > 65535) {
        throw new Error(
            "The Jupyter status response " + "contains an invalid port.",
        );
    }

    return {
        ...data,
        port,
    };
}

async function responseErrorMessage(response) {
    let message = `Jupyter status API returned HTTP ${response.status}.`;

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
        console.debug(
            "Unable to parse Jupyter status API error response:",
            error,
        );
    }

    return message;
}

export async function requestJupyterStatus() {
    const response = await fetch(JUPYTER_STATUS_URL, {
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
