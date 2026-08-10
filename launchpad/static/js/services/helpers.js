"use strict";

/* Formatting */

export function formatTimestamp(date) {
    return new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit",
        second: "2-digit",
    }).format(date);
}

export function formatLabel(value) {
    if (value === null || value === undefined || value === "") {
        return "Unknown";
    }

    return String(value)
        .replaceAll("-", " ")
        .replaceAll("_", " ")
        .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function stateLabel(state) {
    const labels = {
        running: "Running",
        completed: "Completed",
        waiting: "Waiting",
        starting: "Starting",
        stopping: "Stopping",
        reloading: "Reloading",
        inactive: "Inactive",
        failed: "Failed",
        "not-installed": "Not Installed",
        unknown: "Unknown",
    };

    return labels[state] ?? formatLabel(state);
}

export function startupLabel(startup) {
    const labels = {
        continuous: "Continuous",
        oneshot: "One-Time Startup",
        conditional: "Conditional",
    };

    return labels[startup] ?? formatLabel(startup);
}

export function categoryLabel(category) {
    const labels = {
        boot: "Boot Service",
        background: "Background Service",
        web: "Web Service",
        network: "Network Service",
    };

    return labels[category] ?? formatLabel(category);
}

/* Classification */

export function healthClass(health) {
    if (health === "healthy") {
        return "status-healthy";
    }

    if (health === "warning") {
        return "status-warning";
    }

    if (health === "error") {
        return "status-error";
    }

    return "status-unknown";
}

export function serviceCardClass(health) {
    if (health === "healthy") {
        return "service-card-healthy";
    }

    if (health === "warning") {
        return "service-card-warning";
    }

    if (health === "error") {
        return "service-card-error";
    }

    return "service-card-unknown";
}

export function overallState(summary) {
    const errorCount = Number(summary.error ?? 0);

    const warningCount = Number(summary.warning ?? 0);

    const unknownCount = Number(summary.unknown ?? 0);

    if (errorCount > 0) {
        return {
            label: "Critical",
            className: "status-error",
        };
    }

    if (warningCount > 0 || unknownCount > 0) {
        return {
            label: "Needs Attention",
            className: "status-warning",
        };
    }

    return {
        label: "Healthy",
        className: "status-healthy",
    };
}
