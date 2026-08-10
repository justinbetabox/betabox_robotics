"use strict";

export function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
}

export function formatVoltage(value) {
    const voltage = Number(value);

    if (!Number.isFinite(voltage)) {
        return "--";
    }

    return `${voltage.toFixed(2)} V`;
}

export function formatTemperature(value) {
    const temperature = Number(value);

    if (!Number.isFinite(temperature)) {
        return "--";
    }

    return `${temperature.toFixed(1)} °C`;
}

export function determineHealth(status) {
    const hardware = status.hardware ?? {};

    const battery = hardware.battery ?? {};

    const vision = hardware.vision ?? {};

    const systemHealth = status.system_health ?? {};

    const temperature = systemHealth.temperature ?? {};

    const throttling = systemHealth.throttling ?? {};

    const hasBatteryState = typeof battery.state === "string";

    const hasTemperatureState = typeof temperature.state === "string";

    const hasVisionState = typeof vision.service_available === "boolean";

    if (!hasBatteryState && !hasTemperatureState && !hasVisionState) {
        return {
            label: "Unknown",
            cssClass: "hud-unknown",
        };
    }

    if (
        battery.state === "critical" ||
        temperature.state === "critical" ||
        throttling.undervoltage_now === true
    ) {
        return {
            label: "Needs Attention",
            cssClass: "hud-critical",
        };
    }

    if (
        battery.available === false ||
        battery.state === "low" ||
        temperature.state === "warning" ||
        throttling.throttled_now === true ||
        vision.service_available === false
    ) {
        return {
            label: "Warning",
            cssClass: "hud-warning",
        };
    }

    return {
        label: "Healthy",
        cssClass: "hud-healthy",
    };
}

export function shapeAxis(value, deadZone, exponent) {
    const magnitude = Math.abs(value);

    if (magnitude <= deadZone) {
        return 0;
    }

    const normalized = (magnitude - deadZone) / (1 - deadZone);

    const curved = Math.pow(normalized, exponent);

    return Math.sign(value) * curved;
}

export function describeControlState(throttle, steering) {
    const throttlePercent = Math.round(Math.abs(throttle) * 100);

    let motionText = "Stopped";

    if (throttle > 0) {
        motionText = `Forward ${throttlePercent}%`;
    } else if (throttle < 0) {
        motionText = `Reverse ${throttlePercent}%`;
    }

    if (steering < 0) {
        return `${motionText} · Left`;
    }

    if (steering > 0) {
        return `${motionText} · Right`;
    }

    return motionText;
}

export function keyboardControlForKey(key) {
    const normalized = key.toLowerCase();

    const controls = {
        w: "keyboardForward",
        arrowup: "keyboardForward",

        s: "keyboardBackward",
        arrowdown: "keyboardBackward",

        a: "keyboardLeft",
        arrowleft: "keyboardLeft",

        d: "keyboardRight",
        arrowright: "keyboardRight",
    };

    return controls[normalized];
}
