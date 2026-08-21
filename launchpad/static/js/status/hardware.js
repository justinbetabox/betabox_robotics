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

    const sensors = data.hardware?.sensors ?? {};

    const vision = data.hardware?.vision ?? {};

    const runtime = data.runtime ?? {};

    const grayscaleValues = Array.isArray(sensors.grayscale_values)
        ? sensors.grayscale_values.join(", ")
        : "Unavailable";

    const ultrasonicDistance =
        typeof sensors.ultrasonic_distance === "number"
            ? `${sensors.ultrasonic_distance.toFixed(1)} cm`
            : "Unavailable";

    renderDetailItems(elements.hardwareStatus, [
        ["Battery Voltage", formatVoltage(battery.voltage)],
        ["Battery State", formatState(battery.state)],

        ["Grayscale Available", formatBoolean(sensors.grayscale_available)],
        ["Grayscale Plausible", formatBoolean(sensors.grayscale_plausible)],
        ["Grayscale Values", grayscaleValues],

        ["Ultrasonic Configured", formatBoolean(sensors.ultrasonic_configured)],
        ["Ultrasonic Available", formatBoolean(sensors.ultrasonic_available)],
        ["Ultrasonic Distance", ultrasonicDistance],

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
        ["Vision Running", formatBoolean(vision.running)],
        ["Camera Running", formatBoolean(vision.camera_running)],
        ["Vision Frame Available", formatBoolean(vision.camera_has_frame)],
        ["Vision Clients", String(vision.clients ?? 0)],
    ]);
}
