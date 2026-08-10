"use strict";

import {
    DRIVE_DEAD_ZONE,
    DRIVE_SEND_INTERVAL_MS,
    DRIVE_STEERING_CURVE,
    DRIVE_THROTTLE_CURVE,
} from "./constants.js";

import { elements } from "./dom.js";

import { describeControlState, shapeAxis } from "./helpers.js";

import { state } from "./state.js";

let resetDriveInterface = null;

export function setDriveResetHandler(handler) {
    if (handler !== null && typeof handler !== "function") {
        throw new TypeError("handler must be a function or null");
    }

    resetDriveInterface = handler;
}

export function effectiveThrottle() {
    let raw = 0;

    if (state.joystickActive) {
        raw = -state.joystickY;
    } else if (state.keyboardForward && !state.keyboardBackward) {
        raw = 1;
    } else if (state.keyboardBackward && !state.keyboardForward) {
        raw = -1;
    }

    return shapeAxis(raw, DRIVE_DEAD_ZONE, DRIVE_THROTTLE_CURVE);
}

export function effectiveSteering() {
    let raw = 0;

    if (state.joystickActive) {
        raw = state.joystickX;
    } else if (state.keyboardLeft && !state.keyboardRight) {
        raw = -1;
    } else if (state.keyboardRight && !state.keyboardLeft) {
        raw = 1;
    }

    return shapeAxis(raw, DRIVE_DEAD_ZONE, DRIVE_STEERING_CURVE);
}

export function sendJson(message) {
    if (
        state.websocket === null ||
        state.websocket.readyState !== WebSocket.OPEN
    ) {
        return false;
    }

    state.websocket.send(JSON.stringify(message));

    return true;
}

export function sendDriveState(force = false) {
    if (!state.ready) {
        return;
    }

    if (force && state.pendingDriveTimer !== null) {
        window.clearTimeout(state.pendingDriveTimer);

        state.pendingDriveTimer = null;
    }

    const now = performance.now();

    const elapsed = now - state.lastDriveSendTime;

    if (!force && elapsed < DRIVE_SEND_INTERVAL_MS) {
        if (state.pendingDriveTimer === null) {
            state.pendingDriveTimer = window.setTimeout(() => {
                state.pendingDriveTimer = null;

                sendDriveState(true);
            }, DRIVE_SEND_INTERVAL_MS - elapsed);
        }

        return;
    }

    state.lastDriveSendTime = now;

    const maximumThrottle = state.speed / 100;

    const throttle = effectiveThrottle() * maximumThrottle;

    const steering = effectiveSteering();

    const controlState = {
        throttle,
        steering,
        camera_pan: state.cameraPan,
        camera_tilt: state.cameraTilt,
        headlights: state.headlights,
        horn: state.horn,
    };

    const serialized = JSON.stringify(controlState);

    if (!force && serialized === state.lastCommand) {
        return;
    }

    state.lastCommand = serialized;

    sendJson({
        type: "control",
        ...controlState,
    });

    elements.command.textContent = describeControlState(throttle, steering);
}

export function resetLocalControls() {
    if (state.pendingDriveTimer !== null) {
        window.clearTimeout(state.pendingDriveTimer);

        state.pendingDriveTimer = null;
    }

    state.keyboardForward = false;

    state.keyboardBackward = false;

    state.keyboardLeft = false;

    state.keyboardRight = false;

    state.joystickActive = false;

    state.joystickX = 0;

    state.joystickY = 0;

    state.lastCommand = "";

    elements.command.textContent = "Stopped";

    if (resetDriveInterface !== null) {
        resetDriveInterface();
    }
}

export function stopAndResetControls() {
    if (
        state.ready &&
        state.websocket !== null &&
        state.websocket.readyState === WebSocket.OPEN
    ) {
        sendJson({
            type: "stop",
        });
    }

    resetLocalControls();
}

export function emergencyStop() {
    stopAndResetControls();
}
