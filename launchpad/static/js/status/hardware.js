"use strict";

import { elements } from "./dom.js";

import {
    formatBoolean,
    formatState,
    formatVoltage,
    renderDetailItems,
} from "./helpers.js";

export function renderHardware(data) {
    const battery = data.hardware?.battery ?? {};

    const vision = data.hardware?.vision ?? {};

    const runtime = data.runtime ?? {};

    renderDetailItems(elements.hardwareStatus, [
        ["Battery Voltage", formatVoltage(battery.voltage)],
        ["Battery State", formatState(battery.state)],
        ["Runtime Ready", formatBoolean(runtime.ready)],
        ["Hardware Owned", formatBoolean(runtime.ownership_acquired)],
        ["Hardware Initialized", formatBoolean(runtime.hardware_initialized)],
        [
            "Control Owner",
            runtime.control_owner ? String(runtime.control_owner) : "None",
        ],
        [
            "Vision Service",
            vision.service_available ? "Available" : "Unavailable",
        ],
        ["Vision Running", formatBoolean(vision.camera_running)],
        ["Vision Frame Available", formatBoolean(vision.camera_has_frame)],
        ["Vision Clients", String(vision.clients ?? 0)],
    ]);
}
