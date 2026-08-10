"use strict";

function requireElement(selector, expectedType = HTMLElement) {
    const found = document.querySelector(selector);

    if (!(found instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return found;
}

export const elements = {
    connection: requireElement("#diagnostics-connection"),

    runButton: requireElement("#run-diagnostics", HTMLButtonElement),

    retryButton: requireElement("#retry-diagnostics", HTMLButtonElement),

    updated: requireElement("#diagnostics-updated"),

    overallIndicator: requireElement("#overall-indicator"),

    overallStatus: requireElement("#overall-status"),

    healthyCount: requireElement("#healthy-count"),

    warningCount: requireElement("#warning-count"),

    errorCount: requireElement("#error-count"),

    criticalCount: requireElement("#critical-count"),

    totalCount: requireElement("#total-count"),

    issuesSection: requireElement("#issues-section"),

    issuesSummary: requireElement("#issues-summary"),

    issuesList: requireElement("#issues-list"),

    diagnosticsList: requireElement("#diagnostics-list"),

    errorPanel: requireElement("#diagnostics-error-panel"),

    errorMessage: requireElement("#diagnostics-error-message"),
};
