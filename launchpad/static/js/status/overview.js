"use strict";

import { determineOverallStatus } from "./attention.js";

import { elements } from "./dom.js";

import {
    controlLabel,
    formatTemperature,
    formatVoltage,
    statusClass,
    visionLabel,
} from "./helpers.js";

/* Overall health */

function setOverallStatus(label, state) {
    elements.overallStatus.textContent = label;

    elements.overallIndicator.classList.remove(
        "status-healthy",
        "status-warning",
        "status-critical",
        "status-unknown",
    );

    elements.overallIndicator.classList.add(`status-${statusClass(state)}`);
}

/* Service summary */

function renderServiceSummary(data) {
    const states = Object.values(data.services ?? {});

    const activeCount = states.filter((state) => state === "active").length;

    const failedCount = states.filter((state) => state === "failed").length;

    const otherCount = states.length - activeCount - failedCount;

    const parts = [`${activeCount} active`];

    if (failedCount > 0) {
        parts.push(`${failedCount} failed`);
    }

    if (otherCount > 0) {
        parts.push(`${otherCount} other`);
    }

    elements.servicesStatus.textContent = parts.join(" · ");
}

/* Overview */

export function renderOverview(data) {
    const overall = determineOverallStatus(data);

    setOverallStatus(overall.label, overall.state);

    const control = data.control ?? {};

    const battery = data.hardware?.battery ?? {};

    const vision = data.hardware?.vision ?? {};

    const temperature = data.system_health?.temperature ?? {};

    const jupyterhub = data.jupyterhub ?? {};

    elements.batteryStatus.textContent = formatVoltage(battery.voltage);

    elements.temperatureStatus.textContent = formatTemperature(
        temperature.celsius,
    );

    elements.robotStatus.textContent = controlLabel(control);

    elements.visionStatus.textContent = visionLabel(vision);

    elements.jupyterStatus.textContent = jupyterhub.responding
        ? "Online"
        : jupyterhub.active
          ? "Not Responding"
          : "Offline";

    renderServiceSummary(data);
}
