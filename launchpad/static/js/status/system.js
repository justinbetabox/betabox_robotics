"use strict";

import { elements } from "./dom.js";

import {
    formatGigabytes,
    formatMegabytes,
    formatPercent,
    formatState,
    formatTemperature,
    renderDetailItems,
} from "./helpers.js";

export function renderSystem(data) {
    const health = data.system_health ?? {};

    const temperature = health.temperature ?? {};

    const throttling = health.throttling ?? {};

    const memory = health.memory ?? {};

    const disk = health.disk ?? {};

    renderDetailItems(elements.systemStatus, [
        ["Platform Version", data.version ?? "Unavailable"],
        ["Hostname", data.hostname ?? "Unavailable"],
        ["CPU Temperature", formatTemperature(temperature.celsius)],
        ["Temperature State", formatState(temperature.state)],
        ["Memory Used", formatPercent(memory.used_percent)],
        ["Memory Available", formatMegabytes(memory.available_mb)],
        ["Memory Total", formatMegabytes(memory.total_mb)],
        ["Disk Used", formatPercent(disk.used_percent)],
        ["Disk Free", formatGigabytes(disk.free_gb)],
        ["Disk Total", formatGigabytes(disk.total_gb)],
        ["Undervoltage Now", throttling.undervoltage_now ? "Detected" : "No"],
        [
            "Undervoltage Since Boot",
            throttling.undervoltage_occurred ? "Detected" : "No",
        ],
        ["Throttled Now", throttling.throttled_now ? "Yes" : "No"],
        ["Throttled Since Boot", throttling.throttled_occurred ? "Yes" : "No"],
        ["Throttle Flags", throttling.raw ?? "Unavailable"],
    ]);
}
