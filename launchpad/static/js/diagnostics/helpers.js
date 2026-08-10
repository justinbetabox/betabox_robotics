"use strict";

/* Formatting */

export function formatTimestamp(date) {
    return new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit",
        second: "2-digit",
    }).format(date);
}

/* Classification */

export function severityLabel(severity, ok) {
    if (ok) {
        return "Healthy";
    }

    const labels = {
        warning: "Warning",
        error: "Error",
        critical: "Critical",
        info: "Information",
    };

    return labels[severity] ?? "Unknown";
}

export function statusClass(severity, ok) {
    if (ok) {
        return "status-healthy";
    }

    if (severity === "warning") {
        return "status-warning";
    }

    if (severity === "error" || severity === "critical") {
        return "status-error";
    }

    return "status-unknown";
}

export function cardClass(severity, ok) {
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

export function badgeClass(severity, ok) {
    if (ok) {
        return "diagnosis-badge-healthy";
    }

    if (
        severity === "warning" ||
        severity === "error" ||
        severity === "critical" ||
        severity === "info"
    ) {
        return `diagnosis-badge-${severity}`;
    }

    return "diagnosis-badge-info";
}

export function overallPresentation(summary) {
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
