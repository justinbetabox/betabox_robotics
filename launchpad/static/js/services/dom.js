"use strict";

function requireElement(selector, expectedType = HTMLElement) {
    const found = document.querySelector(selector);

    if (!(found instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return found;
}

export const elements = {
    connection: requireElement("#services-connection"),

    refreshButton: requireElement("#refresh-services", HTMLButtonElement),

    retryButton: requireElement("#retry-services", HTMLButtonElement),

    updated: requireElement("#services-updated"),

    overallIndicator: requireElement("#overall-indicator"),

    overallStatus: requireElement("#overall-status"),

    healthyCount: requireElement("#healthy-count"),

    warningCount: requireElement("#warning-count"),

    errorCount: requireElement("#error-count"),

    unknownCount: requireElement("#unknown-count"),

    totalCount: requireElement("#total-count"),

    attentionSection: requireElement("#attention-section"),

    attentionList: requireElement("#attention-list"),

    servicesList: requireElement("#services-list"),

    errorPanel: requireElement("#services-error-panel"),

    errorMessage: requireElement("#services-error-message"),
};
