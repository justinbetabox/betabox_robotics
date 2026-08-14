"use strict";

import { elements } from "./dom.js";

import {
    formatPercent,
    formatState,
    formatTemperature,
    formatVoltage,
    serviceDisplayName,
} from "./helpers.js";

/* Attention classification */

export function collectAttentionItems(data) {
    const items = [];

    for (const [service, state] of Object.entries(data.services ?? {})) {
        if (state === "failed") {
            items.push({
                title: serviceDisplayName(service),
                message: `${service} has failed.`,
                severity: "critical",
            });

            continue;
        }

        if (state !== "active" && state !== "inactive") {
            items.push({
                title: serviceDisplayName(service),
                message: `${service} reported ${formatState(state)}.`,
                severity: "warning",
            });
        }
    }

    const passiveHardwareAvailable = data.hardware?.passive_hardware_available;

    if (passiveHardwareAvailable === false) {
        items.push({
            title: "Robot Hardware Unavailable",
            message:
                "The Robot HAT is not responding. " +
                "Check that the Robot HAT power switch is on.",
            severity: "critical",
        });
    }

    const battery = data.hardware?.battery ?? {};

    if (battery.state === "critical") {
        items.push({
            title: "Battery Critical",
            message: `Battery voltage is ${formatVoltage(battery.voltage)}.`,
            severity: "critical",
        });
    } else if (battery.state === "low") {
        items.push({
            title: "Battery Low",
            message: `Battery voltage is ${formatVoltage(battery.voltage)}.`,
            severity: "warning",
        });
    }

    if (passiveHardwareAvailable !== false && battery.error) {
        items.push({
            title: "Battery Reading Error",
            message: String(battery.error),
            severity: "warning",
        });
    }

    const sensors = data.hardware?.sensors ?? {};

    if (passiveHardwareAvailable !== false) {
        if (sensors.grayscale_available === false) {
            items.push({
                title: "Grayscale Unavailable",
                message: "The grayscale sensor could not be read.",
                severity: "warning",
            });
        } else if (sensors.grayscale_plausible === false) {
            const suspiciousChannels =
                sensors.grayscale_suspicious_channels ?? [];

            let message =
                "The grayscale sensor is reporting abnormal readings.";

            if (suspiciousChannels.length === 3) {
                message = "The grayscale module may be disconnected or faulty.";
            } else if (suspiciousChannels.length > 0) {
                const channelNames = ["left", "middle", "right"];

                const names = suspiciousChannels
                    .map((channel) => channelNames[channel])
                    .filter((name) => name !== undefined);

                if (names.length > 0) {
                    message =
                        `The ${names.join(", ")} grayscale sensor ` +
                        "may be disconnected or faulty.";
                }
            }

            items.push({
                title: "Grayscale Sensor Warning",
                message,
                severity: "warning",
            });
        }
    }

    const vision = data.hardware?.vision ?? {};

    if (!vision.service_available) {
        items.push({
            title: "Vision Service Unavailable",
            message: "The robot vision service could not be reached.",
            severity: "critical",
        });
    } else if (!vision.camera_running || !vision.camera_has_frame) {
        items.push({
            title: "Vision Not Ready",
            message:
                "The vision service is available, but the camera is not producing a usable frame.",
            severity: "warning",
        });
    }

    if (vision.error) {
        items.push({
            title: "Vision Error",
            message: String(vision.error),
            severity: "warning",
        });
    }

    const temperature = data.system_health?.temperature ?? {};

    if (temperature.state === "critical") {
        items.push({
            title: "CPU Temperature Critical",
            message: `Current temperature is ${formatTemperature(temperature.celsius)}.`,
            severity: "critical",
        });
    } else if (temperature.state === "warning") {
        items.push({
            title: "CPU Temperature High",
            message:
                `Current temperature is ` +
                `${formatTemperature(temperature.celsius)}.`,
            severity: "warning",
        });
    }

    const memory = data.system_health?.memory ?? {};

    if (memory.state === "critical") {
        items.push({
            title: "Memory Critical",
            message: `${formatPercent(
                memory.used_percent,
            )} of memory is in use.`,
            severity: "critical",
        });
    } else if (memory.state === "warning") {
        items.push({
            title: "Memory Usage High",
            message: `${formatPercent(
                memory.used_percent,
            )} of memory is in use.`,
            severity: "warning",
        });
    }

    const disk = data.system_health?.disk ?? {};

    if (disk.state === "critical") {
        items.push({
            title: "Disk Space Critical",
            message: `${formatPercent(
                disk.used_percent,
            )} of the disk is in use.`,
            severity: "critical",
        });
    } else if (disk.state === "warning") {
        items.push({
            title: "Disk Usage High",
            message: `${formatPercent(
                disk.used_percent,
            )} of the disk is in use.`,
            severity: "warning",
        });
    }

    const throttling = data.system_health?.throttling ?? {};

    if (throttling.undervoltage_now) {
        items.push({
            title: "Undervoltage Detected",
            message:
                "The Raspberry Pi is currently receiving insufficient power.",
            severity: "critical",
        });
    }

    if (throttling.throttled_now) {
        items.push({
            title: "CPU Throttling",
            message: "The Raspberry Pi is currently reducing performance.",
            severity: "warning",
        });
    }

    if (throttling.undervoltage_occurred && !throttling.undervoltage_now) {
        items.push({
            title: "Previous Undervoltage",
            message:
                "The Raspberry Pi detected an undervoltage condition since boot.",
            severity: "warning",
        });
    }

    if (throttling.throttled_occurred && !throttling.throttled_now) {
        items.push({
            title: "Previous CPU Throttling",
            message: "The Raspberry Pi was throttled at least once since boot.",
            severity: "warning",
        });
    }

    if (data.jupyterhub?.active && !data.jupyterhub?.responding) {
        items.push({
            title: "JupyterHub Not Responding",
            message:
                data.jupyterhub.message ??
                "The service is active but its HTTP endpoint is unavailable.",
            severity: "warning",
        });
    }

    return items;
}

/* Overall classification */

export function determineOverallStatus(data) {
    const attentionItems = collectAttentionItems(data);

    const hasCritical = attentionItems.some(
        (item) => item.severity === "critical",
    );

    if (hasCritical) {
        return {
            label: "Critical",
            state: "critical",
        };
    }

    if (attentionItems.length > 0) {
        return {
            label: "Needs Attention",
            state: "warning",
        };
    }

    return {
        label: "Healthy",
        state: "healthy",
    };
}

/* Rendering */

function createAttentionItem(title, message, severity) {
    const item = document.createElement("article");

    item.className = `attention-item attention-${severity}`;

    const indicator = document.createElement("span");

    indicator.className = `status-dot status-${severity}`;

    indicator.setAttribute("aria-hidden", "true");

    const text = document.createElement("div");

    const heading = document.createElement("h3");

    heading.textContent = title;

    const description = document.createElement("p");

    description.textContent = message;

    text.append(heading, description);

    item.append(indicator, text);

    return item;
}

export function renderAttention(data) {
    const items = collectAttentionItems(data);

    elements.attentionList.replaceChildren();

    if (items.length === 0) {
        elements.attentionSection.hidden = true;

        return;
    }

    for (const item of items) {
        elements.attentionList.append(
            createAttentionItem(item.title, item.message, item.severity),
        );
    }

    elements.attentionSection.hidden = false;
}
