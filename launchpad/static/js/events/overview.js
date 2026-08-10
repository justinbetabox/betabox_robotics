"use strict";

import { elements } from "./dom.js";

import { overviewStatusClass } from "./helpers.js";

export function renderOverview(summary) {
    elements.totalCount.textContent = String(summary.total ?? 0);

    elements.availableCount.textContent = String(summary.total_available ?? 0);

    elements.infoCount.textContent = String(summary.info ?? 0);

    elements.warningCount.textContent = String(summary.warning ?? 0);

    elements.errorCount.textContent = String(summary.error ?? 0);

    elements.criticalCount.textContent = String(summary.critical ?? 0);

    elements.overviewIndicator.classList.remove(
        "status-info",
        "status-warning",
        "status-error",
        "status-unknown",
    );

    elements.overviewIndicator.classList.add(overviewStatusClass(summary));
}
