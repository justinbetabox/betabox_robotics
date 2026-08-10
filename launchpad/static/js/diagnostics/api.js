"use strict";

import { DIAGNOSTICS_API_URL } from "./constants.js";

/* Validation */

function normalizeDiagnosis(diagnosis) {
    if (
        diagnosis === null ||
        typeof diagnosis !== "object" ||
        Array.isArray(diagnosis) ||
        typeof diagnosis.ok !== "boolean"
    ) {
        throw new Error("The diagnostics response contains an invalid result.");
    }

    return {
        ...diagnosis,

        title:
            typeof diagnosis.title === "string"
                ? diagnosis.title
                : "Diagnostic Check",

        summary:
            typeof diagnosis.summary === "string"
                ? diagnosis.summary
                : "No diagnostic summary is available.",

        severity:
            typeof diagnosis.severity === "string"
                ? diagnosis.severity
                : "unknown",

        causes: Array.isArray(diagnosis.causes) ? diagnosis.causes : [],

        affected: Array.isArray(diagnosis.affected) ? diagnosis.affected : [],

        actions: Array.isArray(diagnosis.actions) ? diagnosis.actions : [],
    };
}

function validatePayload(payload) {
    if (
        payload === null ||
        typeof payload !== "object" ||
        Array.isArray(payload)
    ) {
        throw new Error("The diagnostics API returned an invalid response.");
    }

    if (
        payload.summary === null ||
        typeof payload.summary !== "object" ||
        Array.isArray(payload.summary)
    ) {
        throw new Error("The diagnostics response does not include a summary.");
    }

    if (!Array.isArray(payload.diagnoses)) {
        throw new Error("The diagnostics response does not include results.");
    }

    return {
        ...payload,

        diagnoses: payload.diagnoses.map(normalizeDiagnosis),
    };
}

/* Error responses */

async function responseErrorMessage(response) {
    let message = `Diagnostics API returned HTTP ${response.status}.`;

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
        console.debug("Unable to parse diagnostics API error response:", error);
    }

    return message;
}

/* API */

export async function requestDiagnostics() {
    const response = await fetch(DIAGNOSTICS_API_URL, {
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
