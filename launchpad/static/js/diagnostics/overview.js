"use strict";

import { elements } from "./dom.js";

import { overallPresentation } from "./helpers.js";

export function renderOverview(summary) {
    const overall = overallPresentation(summary);

    elements.overallStatus.textContent = overall.label;

    elements.overallIndicator.classList.remove(
        "status-healthy",
        "status-warning",
        "status-error",
        "status-unknown",
    );

    elements.overallIndicator.classList.add(overall.className);

    elements.healthyCount.textContent = summary.healthy ?? 0;

    elements.warningCount.textContent = summary.warning ?? 0;

    elements.errorCount.textContent = summary.error ?? 0;

    elements.criticalCount.textContent = summary.critical ?? 0;

    elements.totalCount.textContent = summary.total ?? 0;
}
