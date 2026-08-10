"use strict";

import { INFORMATION_API_URL } from "./constants.js";

/* Validation */

function requireObject(value, name) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
        throw new Error(`The information response is missing ${name}.`);
    }

    return value;
}

function normalizePayload(payload) {
    if (
        payload === null ||
        typeof payload !== "object" ||
        Array.isArray(payload)
    ) {
        throw new Error("The Information API returned an invalid response.");
    }

    return {
        ...payload,

        robot: requireObject(payload.robot, "robot"),

        network: requireObject(payload.network, "network"),

        software: requireObject(payload.software, "software"),

        storage: requireObject(payload.storage, "storage"),

        media: requireObject(payload.media, "media"),

        features: requireObject(payload.features, "features"),
    };
}

/* Error responses */

async function responseErrorMessage(response) {
    let message = `Information API returned HTTP ${response.status}.`;

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
        console.debug("Unable to parse Information API error response:", error);
    }

    return message;
}

/* API */

export async function requestInformation() {
    const response = await fetch(INFORMATION_API_URL, {
        method: "GET",
        headers: {
            Accept: "application/json",
        },
        cache: "no-store",
    });

    if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
    }

    return normalizePayload(await response.json());
}
