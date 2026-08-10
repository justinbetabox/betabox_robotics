"use strict";

function requireElement(selector, expectedType = HTMLElement) {
    const element = document.querySelector(selector);

    if (!(element instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return element;
}

export const elements = {
    connection: requireElement("#status-connection"),

    updated: requireElement("#status-updated"),

    refreshButton: requireElement("#refresh-status", HTMLButtonElement),

    retryButton: requireElement("#retry-status", HTMLButtonElement),

    overallIndicator: requireElement("#overall-indicator"),

    overallStatus: requireElement("#overall-status"),

    batteryStatus: requireElement("#battery-status"),

    temperatureStatus: requireElement("#temperature-status"),

    robotStatus: requireElement("#robot-status"),

    visionStatus: requireElement("#vision-status"),

    jupyterStatus: requireElement("#jupyter-status"),

    servicesStatus: requireElement("#services-status"),

    attentionSection: requireElement("#attention-section"),

    attentionList: requireElement("#attention-list"),

    hardwareStatus: requireElement("#hardware-status"),

    systemStatus: requireElement("#system-status"),

    networkStatus: requireElement("#network-status"),

    errorPanel: requireElement("#status-error-panel"),

    errorMessage: requireElement("#status-error-message"),
};
