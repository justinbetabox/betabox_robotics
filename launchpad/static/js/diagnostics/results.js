"use strict";

import { elements } from "./dom.js";

import {
    badgeClass,
    cardClass,
    severityLabel,
    statusClass,
} from "./helpers.js";

/* Diagnosis details */

function createListSection(title, values, className) {
    if (!Array.isArray(values) || values.length === 0) {
        return null;
    }

    const section = document.createElement("div");

    section.className = className;

    const heading = document.createElement("h4");

    heading.textContent = title;

    const list = document.createElement("ul");

    for (const value of values) {
        const item = document.createElement("li");

        item.textContent = String(value);

        list.append(item);
    }

    section.append(heading, list);

    return section;
}

/* Diagnosis card */

export function createDiagnosisCard(diagnosis, { compact = false } = {}) {
    const article = document.createElement("article");

    article.className = [
        "diagnosis-card",
        cardClass(diagnosis.severity, diagnosis.ok),
        compact ? "diagnosis-card-compact" : "",
    ]
        .filter(Boolean)
        .join(" ");

    const header = document.createElement("div");

    header.className = "diagnosis-header";

    const identity = document.createElement("div");

    identity.className = "diagnosis-identity";

    const indicator = document.createElement("span");

    indicator.className = [
        "status-dot",
        statusClass(diagnosis.severity, diagnosis.ok),
    ].join(" ");

    indicator.setAttribute("aria-hidden", "true");

    const title = document.createElement("h3");

    title.textContent = diagnosis.title || "Diagnostic Check";

    identity.append(indicator, title);

    const badge = document.createElement("span");

    badge.className = [
        "diagnosis-badge",
        badgeClass(diagnosis.severity, diagnosis.ok),
    ].join(" ");

    badge.textContent = severityLabel(diagnosis.severity, diagnosis.ok);

    header.append(identity, badge);

    const summary = document.createElement("p");

    summary.className = "diagnosis-summary";

    summary.textContent =
        diagnosis.summary || "No diagnostic summary is available.";

    article.append(header, summary);

    const detailSections = [
        createListSection(
            "Likely Causes",
            diagnosis.causes,
            "diagnosis-detail diagnosis-causes",
        ),
        createListSection(
            "Affected Components",
            diagnosis.affected,
            "diagnosis-detail diagnosis-affected",
        ),
        createListSection(
            "Recommended Actions",
            diagnosis.actions,
            "diagnosis-detail diagnosis-actions",
        ),
    ].filter(Boolean);

    if (detailSections.length > 0 && !compact) {
        const details = document.createElement("details");

        details.className = "diagnosis-details";

        if (!diagnosis.ok) {
            details.open = true;
        }

        const detailsSummary = document.createElement("summary");

        detailsSummary.textContent = diagnosis.ok
            ? "View details"
            : "View troubleshooting details";

        const detailGrid = document.createElement("div");

        detailGrid.className = "diagnosis-detail-grid";

        detailGrid.append(...detailSections);

        details.append(detailsSummary, detailGrid);

        article.append(details);
    }

    return article;
}

/* Complete results */

export function renderDiagnoses(diagnoses) {
    elements.diagnosticsList.replaceChildren();

    if (!Array.isArray(diagnoses) || diagnoses.length === 0) {
        const empty = document.createElement("div");

        empty.className = "empty-state diagnostics-empty";

        empty.textContent = "No diagnostic results were returned.";

        elements.diagnosticsList.append(empty);

        return;
    }

    for (const diagnosis of diagnoses) {
        elements.diagnosticsList.append(createDiagnosisCard(diagnosis));
    }
}
