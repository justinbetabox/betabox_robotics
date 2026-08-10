"use strict";

import { SERVICES_API_URL } from "./constants.js";

/* Validation */

function normalizeService(service) {
    if (
        service === null ||
        typeof service !== "object" ||
        Array.isArray(service)
    ) {
        throw new Error("The services response contains an invalid service.");
    }

    const unit = typeof service.unit === "string" ? service.unit : "";

    const name = typeof service.name === "string" ? service.name : "";

    const displayName =
        typeof service.display_name === "string" &&
        service.display_name.trim() !== ""
            ? service.display_name
            : name || unit || "Unknown Service";

    return {
        ...service,

        unit,

        name,

        display_name: displayName,

        description:
            typeof service.description === "string" ? service.description : "",

        state: typeof service.state === "string" ? service.state : "unknown",

        health: typeof service.health === "string" ? service.health : "unknown",

        category:
            typeof service.category === "string" ? service.category : "unknown",

        startup:
            typeof service.startup === "string" ? service.startup : "unknown",

        installed: service.installed === true,
    };
}

function normalizeSummary(summary) {
    if (
        summary === null ||
        typeof summary !== "object" ||
        Array.isArray(summary)
    ) {
        throw new Error("The services response does not include a summary.");
    }

    const count = (value) => {
        const number = Number(value);

        return Number.isFinite(number) && number >= 0 ? Math.floor(number) : 0;
    };

    return {
        ...summary,

        healthy: count(summary.healthy),

        warning: count(summary.warning),

        error: count(summary.error),

        unknown: count(summary.unknown),

        total: count(summary.total),
    };
}

function validatePayload(payload) {
    if (
        payload === null ||
        typeof payload !== "object" ||
        Array.isArray(payload)
    ) {
        throw new Error("The services API returned an invalid response.");
    }

    if (!Array.isArray(payload.services)) {
        throw new Error(
            "The services response does not include a service list.",
        );
    }

    return {
        ...payload,

        summary: normalizeSummary(payload.summary),

        services: payload.services.map(normalizeService),
    };
}

/* Error responses */

async function responseErrorMessage(response) {
    let message = `Services API returned HTTP ${response.status}.`;

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
        console.debug("Unable to parse services API error response:", error);
    }

    return message;
}

/* API */

export async function requestServices() {
    const response = await fetch(SERVICES_API_URL, {
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
