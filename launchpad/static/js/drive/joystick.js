"use strict";

import {
    effectiveSteering,
    effectiveThrottle,
    emergencyStop,
    sendDriveState,
    setDriveResetHandler,
} from "./commands.js";

import { elements } from "./dom.js";

import { clamp, keyboardControlForKey } from "./helpers.js";

import { state } from "./state.js";

function positionDriveStick() {
    const bounds = elements.driveJoystick.getBoundingClientRect();

    const maximumDistance = bounds.width * 0.34;

    elements.driveStick.style.transform = `translate(
            ${state.joystickX * maximumDistance}px,
            ${state.joystickY * maximumDistance}px
        )`;
}

function updateJoystickReadout() {
    const throttle = effectiveThrottle() * (state.speed / 100);

    const steering = effectiveSteering();

    elements.throttleValue.textContent = `${Math.round(throttle * 100)}%`;

    let steeringText = "Center";

    if (steering < 0) {
        steeringText = `Left ${Math.round(Math.abs(steering) * 100)}%`;
    } else if (steering > 0) {
        steeringText = `Right ${Math.round(steering * 100)}%`;
    }

    elements.steeringValue.textContent = steeringText;
}

function setJoystickFromPointer(event) {
    const bounds = elements.driveJoystick.getBoundingClientRect();

    const centerX = bounds.left + bounds.width / 2;

    const centerY = bounds.top + bounds.height / 2;

    const radius = Math.min(bounds.width, bounds.height) / 2;

    let x = (event.clientX - centerX) / radius;

    let y = (event.clientY - centerY) / radius;

    const magnitude = Math.hypot(x, y);

    if (magnitude > 1) {
        x /= magnitude;

        y /= magnitude;
    }

    state.joystickX = clamp(x, -1, 1);

    state.joystickY = clamp(y, -1, 1);

    positionDriveStick();

    updateJoystickReadout();

    sendDriveState();
}

export function resetJoystickInterface() {
    state.joystickActive = false;

    state.joystickX = 0;

    state.joystickY = 0;

    positionDriveStick();

    updateJoystickReadout();
}

function releaseJoystick(event) {
    if (!state.joystickActive) {
        return;
    }

    event.preventDefault();

    resetJoystickInterface();

    sendDriveState(true);
}

function configurePointerJoystick() {
    elements.driveJoystick.addEventListener("pointerdown", (event) => {
        event.preventDefault();

        state.joystickActive = true;

        elements.driveJoystick.setPointerCapture(event.pointerId);

        setJoystickFromPointer(event);
    });

    elements.driveJoystick.addEventListener("pointermove", (event) => {
        if (!state.joystickActive) {
            return;
        }

        event.preventDefault();

        setJoystickFromPointer(event);
    });

    elements.driveJoystick.addEventListener("pointerup", releaseJoystick);

    elements.driveJoystick.addEventListener("pointercancel", releaseJoystick);

    elements.driveJoystick.addEventListener(
        "lostpointercapture",
        releaseJoystick,
    );
}

function configureKeyboard() {
    window.addEventListener("keydown", (event) => {
        if (event.target instanceof HTMLInputElement) {
            return;
        }

        if (event.code === "Space") {
            event.preventDefault();

            emergencyStop();

            return;
        }

        if (event.repeat) {
            return;
        }

        const control = keyboardControlForKey(event.key);

        if (!control) {
            return;
        }

        event.preventDefault();

        state[control] = true;

        updateJoystickReadout();

        sendDriveState();
    });

    window.addEventListener("keyup", (event) => {
        const control = keyboardControlForKey(event.key);

        if (!control) {
            return;
        }

        event.preventDefault();

        state[control] = false;

        updateJoystickReadout();

        sendDriveState();
    });
}

function configureSpeed() {
    elements.speed.addEventListener("input", () => {
        state.speed = Number(elements.speed.value);

        elements.speedValue.textContent = `${state.speed}%`;

        updateJoystickReadout();

        sendDriveState(true);
    });
}

export function initializeDriveControls() {
    setDriveResetHandler(resetJoystickInterface);

    configureKeyboard();

    configurePointerJoystick();

    configureSpeed();

    resetJoystickInterface();
}
