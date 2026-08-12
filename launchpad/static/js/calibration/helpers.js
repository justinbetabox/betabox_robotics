"use strict";

export function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
}

export function formatOffset(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "—";
    }

    const prefix = number > 0 ? "+" : "";

    return `${prefix}${number.toFixed(1)}°`;
}

export function formatTrim(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "—";
    }

    return number.toFixed(2);
}

export function setBadge(element, text, tone) {
    if (!(element instanceof HTMLElement)) {
        throw new TypeError("element must be an HTMLElement");
    }

    if (typeof text !== "string") {
        throw new TypeError("text must be a string");
    }

    if (typeof tone !== "string") {
        throw new TypeError("tone must be a string");
    }

    element.className =
        tone === "neutral" ? "status-badge" : `status-badge status-${tone}`;

    element.textContent = text;
}

export function showTemporaryMessage(element, message, stillCurrent) {
    if (!(element instanceof HTMLElement)) {
        throw new TypeError("element must be an HTMLElement");
    }

    if (typeof message !== "string") {
        throw new TypeError("message must be a string");
    }

    if (typeof stillCurrent !== "function") {
        throw new TypeError("stillCurrent must be a function");
    }

    element.textContent = message;

    window.setTimeout(() => {
        if (stillCurrent()) {
            element.textContent = "";
        }
    }, 3000);
}
