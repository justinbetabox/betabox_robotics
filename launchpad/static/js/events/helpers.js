"use strict";

/* Time formatting */

export function formatUpdatedTime(date) {
    return new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit",
        second: "2-digit",
    }).format(date);
}

function parseTimestamp(value) {
    if (typeof value !== "string" || value === "" || value === "unknown time") {
        return null;
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return null;
    }

    return date;
}

export function formatEventDate(value) {
    const date = parseTimestamp(value);

    if (date === null) {
        return "Unknown date";
    }

    return new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
    }).format(date);
}

export function formatEventTime(value) {
    const date = parseTimestamp(value);

    if (date === null) {
        return "Unknown time";
    }

    return new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit",
        second: "2-digit",
    }).format(date);
}

/* Severity */

export function severityLabel(severity) {
    const labels = {
        info: "Information",
        warning: "Warning",
        error: "Error",
        critical: "Critical",
    };

    return labels[severity] ?? "Information";
}

export function severityClass(severity) {
    if (severity === "warning") {
        return "event-warning";
    }

    if (severity === "error") {
        return "event-error";
    }

    if (severity === "critical") {
        return "event-critical";
    }

    return "event-info";
}

export function overviewStatusClass(summary) {
    if (Number(summary.critical ?? 0) > 0 || Number(summary.error ?? 0) > 0) {
        return "status-error";
    }

    if (Number(summary.warning ?? 0) > 0) {
        return "status-warning";
    }

    return "status-info";
}
