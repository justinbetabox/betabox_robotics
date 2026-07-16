"use strict";

const DIAGNOSTICS_API_URL = "/api/diagnostics";

const elements = {
    connection: document.getElementById(
        "diagnostics-connection"
    ),

    runButton: document.getElementById(
        "run-diagnostics"
    ),

    retryButton: document.getElementById(
        "retry-diagnostics"
    ),

    updated: document.getElementById(
        "diagnostics-updated"
    ),

    overallIndicator: document.getElementById(
        "overall-indicator"
    ),

    overallStatus: document.getElementById(
        "overall-status"
    ),

    healthyCount: document.getElementById(
        "healthy-count"
    ),

    warningCount: document.getElementById(
        "warning-count"
    ),

    errorCount: document.getElementById(
        "error-count"
    ),

    criticalCount: document.getElementById(
        "critical-count"
    ),

    totalCount: document.getElementById(
        "total-count"
    ),

    issuesSection: document.getElementById(
        "issues-section"
    ),

    issuesSummary: document.getElementById(
        "issues-summary"
    ),

    issuesList: document.getElementById(
        "issues-list"
    ),

    diagnosticsList: document.getElementById(
        "diagnostics-list"
    ),

    errorPanel: document.getElementById(
        "diagnostics-error-panel"
    ),

    errorMessage: document.getElementById(
        "diagnostics-error-message"
    ),
};


function setConnectionState(
    state,
    label
) {
    const connection = elements.connection;

    connection.classList.remove(
        "status-connecting",
        "status-connected",
        "status-error"
    );

    if (state === "connected") {
        connection.classList.add(
            "status-connected"
        );
    } else if (state === "error") {
        connection.classList.add(
            "status-error"
        );
    } else {
        connection.classList.add(
            "status-connecting"
        );
    }

    connection.textContent = label;
}


function setRunningState(
    running
) {
    elements.runButton.disabled = running;
    elements.retryButton.disabled = running;

    elements.runButton.textContent = (
        running
            ? "Running…"
            : "Run Diagnostics"
    );

    if (running) {
        setConnectionState(
            "connecting",
            "Checking…"
        );
    }
}


function showError(
    message
) {
    elements.errorMessage.textContent = message;
    elements.errorPanel.hidden = false;

    setConnectionState(
        "error",
        "Unavailable"
    );
}


function hideError() {
    elements.errorPanel.hidden = true;
}


function formatTimestamp(
    date
) {
    return new Intl.DateTimeFormat(
        undefined,
        {
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit",
        }
    ).format(date);
}


function severityLabel(
    severity,
    ok
) {
    if (ok) {
        return "Healthy";
    }

    const labels = {
        warning: "Warning",
        error: "Error",
        critical: "Critical",
        info: "Information",
    };

    return labels[severity] || "Unknown";
}


function statusClass(
    severity,
    ok
) {
    if (ok) {
        return "status-healthy";
    }

    if (severity === "warning") {
        return "status-warning";
    }

    if (
        severity === "error"
        || severity === "critical"
    ) {
        return "status-error";
    }

    return "status-unknown";
}


function cardClass(
    severity,
    ok
) {
    if (ok) {
        return "diagnosis-card-healthy";
    }

    if (severity === "warning") {
        return "diagnosis-card-warning";
    }

    if (severity === "error") {
        return "diagnosis-card-error";
    }

    if (severity === "critical") {
        return "diagnosis-card-critical";
    }

    return "diagnosis-card-unknown";
}


function overallPresentation(
    summary
) {
    if (summary.overall === "critical") {
        return {
            label: "Critical Issues",
            className: "status-error",
        };
    }

    if (summary.overall === "error") {
        return {
            label: "Needs Attention",
            className: "status-error",
        };
    }

    if (summary.overall === "warning") {
        return {
            label: "Warnings Found",
            className: "status-warning",
        };
    }

    return {
        label: "Platform Healthy",
        className: "status-healthy",
    };
}


function renderOverview(
    summary
) {
    const overall = overallPresentation(
        summary
    );

    elements.overallStatus.textContent = (
        overall.label
    );

    elements.overallIndicator.classList.remove(
        "status-healthy",
        "status-warning",
        "status-error",
        "status-unknown"
    );

    elements.overallIndicator.classList.add(
        overall.className
    );

    elements.healthyCount.textContent = (
        summary.healthy ?? 0
    );

    elements.warningCount.textContent = (
        summary.warning ?? 0
    );

    elements.errorCount.textContent = (
        summary.error ?? 0
    );

    elements.criticalCount.textContent = (
        summary.critical ?? 0
    );

    elements.totalCount.textContent = (
        summary.total ?? 0
    );
}


function createListSection(
    title,
    values,
    className
) {
    if (
        !Array.isArray(values)
        || values.length === 0
    ) {
        return null;
    }

    const section = document.createElement(
        "div"
    );

    section.className = className;

    const heading = document.createElement(
        "h4"
    );

    heading.textContent = title;

    const list = document.createElement(
        "ul"
    );

    for (const value of values) {
        const item = document.createElement(
            "li"
        );

        item.textContent = value;
        list.append(item);
    }

    section.append(
        heading,
        list
    );

    return section;
}


function createDiagnosisCard(
    diagnosis,
    compact = false
) {
    const article = document.createElement(
        "article"
    );

    article.className = [
        "diagnosis-card",
        cardClass(
            diagnosis.severity,
            diagnosis.ok
        ),
        compact
            ? "diagnosis-card-compact"
            : "",
    ]
        .filter(Boolean)
        .join(" ");

    const header = document.createElement(
        "div"
    );

    header.className = "diagnosis-header";

    const identity = document.createElement(
        "div"
    );

    identity.className = "diagnosis-identity";

    const indicator = document.createElement(
        "span"
    );

    indicator.className = [
        "status-indicator",
        statusClass(
            diagnosis.severity,
            diagnosis.ok
        ),
    ].join(" ");

    indicator.setAttribute(
        "aria-hidden",
        "true"
    );

    const title = document.createElement(
        "h3"
    );

    title.textContent = (
        diagnosis.title
        || "Diagnostic Check"
    );

    identity.append(
        indicator,
        title
    );

    const badge = document.createElement(
        "span"
    );

    badge.className = [
        "diagnosis-badge",
        `diagnosis-badge-${
            diagnosis.ok
                ? "healthy"
                : diagnosis.severity
        }`,
    ].join(" ");

    badge.textContent = severityLabel(
        diagnosis.severity,
        diagnosis.ok
    );

    header.append(
        identity,
        badge
    );

    const summary = document.createElement(
        "p"
    );

    summary.className = "diagnosis-summary";

    summary.textContent = (
        diagnosis.summary
        || "No diagnostic summary is available."
    );

    article.append(
        header,
        summary
    );

    const detailSections = [
        createListSection(
            "Likely Causes",
            diagnosis.causes,
            "diagnosis-detail diagnosis-causes"
        ),
        createListSection(
            "Affected Components",
            diagnosis.affected,
            "diagnosis-detail diagnosis-affected"
        ),
        createListSection(
            "Recommended Actions",
            diagnosis.actions,
            "diagnosis-detail diagnosis-actions"
        ),
    ].filter(Boolean);

    if (
        detailSections.length > 0
        && !compact
    ) {
        const details = document.createElement(
            "details"
        );

        details.className = "diagnosis-details";

        if (!diagnosis.ok) {
            details.open = true;
        }

        const detailsSummary = (
            document.createElement("summary")
        );

        detailsSummary.textContent = (
            diagnosis.ok
                ? "View details"
                : "View troubleshooting details"
        );

        const detailGrid = document.createElement(
            "div"
        );

        detailGrid.className = (
            "diagnosis-detail-grid"
        );

        detailGrid.append(
            ...detailSections
        );

        details.append(
            detailsSummary,
            detailGrid
        );

        article.append(details);
    }

    return article;
}


function renderIssues(
    summary,
    diagnoses
) {
    const issues = diagnoses.filter(
        diagnosis => !diagnosis.ok
    );

    elements.issuesList.replaceChildren();

    if (issues.length === 0) {
        elements.issuesSection.hidden = true;
        return;
    }

    elements.issuesSummary.textContent = (
        `${summary.issues ?? issues.length} `
        + (
            issues.length === 1
                ? "issue detected"
                : "issues detected"
        )
    );

    for (const diagnosis of issues) {
        elements.issuesList.append(
            createDiagnosisCard(
                diagnosis,
                true
            )
        );
    }

    elements.issuesSection.hidden = false;
}


function renderDiagnoses(
    diagnoses
) {
    elements.diagnosticsList.replaceChildren();

    if (
        !Array.isArray(diagnoses)
        || diagnoses.length === 0
    ) {
        const empty = document.createElement(
            "div"
        );

        empty.className = "diagnostics-empty";

        empty.textContent = (
            "No diagnostic results were returned."
        );

        elements.diagnosticsList.append(
            empty
        );

        return;
    }

    for (const diagnosis of diagnoses) {
        elements.diagnosticsList.append(
            createDiagnosisCard(diagnosis)
        );
    }
}


function validatePayload(
    payload
) {
    if (
        !payload
        || typeof payload !== "object"
    ) {
        throw new Error(
            "The diagnostics API returned an invalid response."
        );
    }

    if (
        !payload.summary
        || typeof payload.summary !== "object"
    ) {
        throw new Error(
            "The diagnostics response does not include a summary."
        );
    }

    if (!Array.isArray(payload.diagnoses)) {
        throw new Error(
            "The diagnostics response does not include results."
        );
    }
}


async function runDiagnostics() {
    setRunningState(true);
    hideError();

    elements.updated.textContent = (
        "Running platform diagnostics…"
    );

    try {
        const response = await fetch(
            DIAGNOSTICS_API_URL,
            {
                method: "GET",
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            }
        );

        if (!response.ok) {
            let message = (
                `Diagnostics API returned HTTP `
                + `${response.status}.`
            );

            try {
                const errorPayload = (
                    await response.json()
                );

                if (errorPayload.message) {
                    message = errorPayload.message;
                }
            } catch {
                // Keep the HTTP error message.
            }

            throw new Error(message);
        }

        const payload = await response.json();

        validatePayload(payload);

        renderOverview(payload.summary);

        renderIssues(
            payload.summary,
            payload.diagnoses
        );

        renderDiagnoses(
            payload.diagnoses
        );

        elements.updated.textContent = (
            `Completed ${formatTimestamp(new Date())}`
        );

        setConnectionState(
            "connected",
            "Complete"
        );
    } catch (error) {
        console.error(
            "Unable to run diagnostics:",
            error
        );

        const message = (
            error instanceof Error
                ? error.message
                : "The diagnostics API did not respond."
        );

        showError(message);

        elements.updated.textContent = (
            "Diagnostics unavailable"
        );
    } finally {
        setRunningState(false);
    }
}


function setupEventListeners() {
    elements.runButton.addEventListener(
        "click",
        runDiagnostics
    );

    elements.retryButton.addEventListener(
        "click",
        runDiagnostics
    );
}


function initializeDiagnosticsPage() {
    setupEventListeners();

    // Run once when the page opens so users immediately
    // receive the current platform health report.
    runDiagnostics();
}


if (
    document.readyState === "loading"
) {
    document.addEventListener(
        "DOMContentLoaded",
        initializeDiagnosticsPage
    );
} else {
    initializeDiagnosticsPage();
}
