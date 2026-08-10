"use strict";

import { elements } from "./dom.js";

import { createDiagnosisCard } from "./results.js";

export function renderIssues(summary, diagnoses) {
    const issues = diagnoses.filter((diagnosis) => !diagnosis.ok);

    elements.issuesList.replaceChildren();

    elements.issuesSummary.textContent = "";

    if (issues.length === 0) {
        elements.issuesSection.hidden = true;

        return;
    }

    const issueCount = summary.issues ?? issues.length;

    elements.issuesSummary.textContent = `${issueCount} ${
        issueCount === 1 ? "issue detected" : "issues detected"
    }`;

    for (const diagnosis of issues) {
        elements.issuesList.append(
            createDiagnosisCard(diagnosis, {
                compact: true,
            }),
        );
    }

    elements.issuesSection.hidden = false;
}
