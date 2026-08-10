"use strict";

function requireElement(selector, expectedType = HTMLElement) {
    const element = document.querySelector(selector);

    if (!(element instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return element;
}

export const elements = {
    hostname: requireElement("#hud-hostname"),

    ip: requireElement("#hud-ip"),

    healthDot: requireElement("#hud-health-dot"),

    health: requireElement("#hud-health"),

    battery: requireElement("#hud-battery"),

    control: requireElement("#hud-control"),

    vision: requireElement("#hud-vision"),

    toggle: requireElement("#hud-toggle", HTMLButtonElement),

    details: requireElement("#hud-details"),

    detailBattery: requireElement("#detail-battery"),

    detailTemperature: requireElement("#detail-temperature"),

    detailControl: requireElement("#detail-control"),

    detailNetwork: requireElement("#detail-network"),

    detailJupyter: requireElement("#detail-jupyter"),

    detailMemory: requireElement("#detail-memory"),

    detailDisk: requireElement("#detail-disk"),

    detailVision: requireElement("#detail-vision"),

    updated: requireElement("#hud-updated"),
};
