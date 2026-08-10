"use strict";

import { elements } from "./dom.js";

import { formatBoolean, renderDetailItems } from "./helpers.js";

export function renderNetwork(data) {
    const health = data.system_health ?? {};

    const ethernet = health.ethernet ?? {};

    const wifi = health.wifi ?? {};

    renderDetailItems(elements.networkStatus, [
        [
            "IP Addresses",
            Array.isArray(data.ip_addresses) && data.ip_addresses.length > 0
                ? data.ip_addresses.join(", ")
                : "Unavailable",
        ],
        ["Ethernet Interface", ethernet.name ?? "Unavailable"],
        ["Ethernet Connected", formatBoolean(ethernet.connected)],
        ["Ethernet State", ethernet.state ?? "Unavailable"],
        ["Ethernet Connection", ethernet.connection || "None"],
        ["Wi-Fi Interface", wifi.name ?? "Unavailable"],
        ["Wi-Fi Connected", formatBoolean(wifi.connected)],
        ["Wi-Fi State", wifi.state ?? "Unavailable"],
        ["Wi-Fi Connection", wifi.connection || "None"],
    ]);
}
