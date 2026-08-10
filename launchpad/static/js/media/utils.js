"use strict";

import { elements } from "./dom.js";

export function setHidden(element, hidden) {
    element.hidden = Boolean(hidden);
}

export function announce(message) {
    elements.announcement.textContent = "";

    window.requestAnimationFrame(() => {
        elements.announcement.textContent = String(message);
    });
}

export async function responseErrorMessage(response, fallback) {
    const contentType = response.headers.get("content-type") ?? "";

    if (contentType.includes("application/json")) {
        try {
            const payload = await response.json();

            if (
                payload !== null &&
                typeof payload === "object" &&
                !Array.isArray(payload)
            ) {
                for (const key of ["message", "reason", "error"]) {
                    const value = payload[key];

                    if (typeof value === "string" && value.trim() !== "") {
                        return value.trim();
                    }
                }
            }
        } catch (error) {
            console.debug("Unable to parse Media API error response:", error);

            return fallback;
        }
    }

    try {
        const text = (await response.text()).trim();

        if (text !== "") {
            return text;
        }
    } catch (error) {
        console.debug("Unable to read Media API error response:", error);
    }

    return fallback;
}
