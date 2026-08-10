"use strict";

function requireElement(selector, expectedType = HTMLElement) {
    const element = document.querySelector(selector);

    if (!(element instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return element;
}

export const elements = {
    connection: requireElement("#events-connection"),

    refreshButton: requireElement("#refresh-events", HTMLButtonElement),

    retryButton: requireElement("#retry-events", HTMLButtonElement),

    clearButton: requireElement("#clear-filters", HTMLButtonElement),

    filterForm: requireElement("#events-filter-form", HTMLFormElement),

    severityFilter: requireElement("#severity-filter", HTMLSelectElement),

    componentFilter: requireElement("#component-filter", HTMLSelectElement),

    limitFilter: requireElement("#limit-filter", HTMLSelectElement),

    updated: requireElement("#events-updated"),

    totalCount: requireElement("#total-count"),

    availableCount: requireElement("#available-count"),

    infoCount: requireElement("#info-count"),

    warningCount: requireElement("#warning-count"),

    errorCount: requireElement("#error-count"),

    criticalCount: requireElement("#critical-count"),

    overviewIndicator: requireElement("#events-overview-indicator"),

    listSummary: requireElement("#event-list-summary"),

    eventsList: requireElement("#events-list"),

    errorPanel: requireElement("#events-error-panel"),

    errorMessage: requireElement("#events-error-message"),
};
