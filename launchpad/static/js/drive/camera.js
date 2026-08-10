"use strict";

import { CAMERA_CURVE, CAMERA_DEAD_ZONE } from "./constants.js";

import { sendDriveState } from "./commands.js";

import { elements } from "./dom.js";

import { clamp, shapeAxis } from "./helpers.js";

import { state } from "./state.js";

function positionCameraStick() {
    const bounds = elements.cameraJoystick.getBoundingClientRect();

    const maximumDistance = bounds.width * 0.34;

    elements.cameraStick.style.transform = `translate(
            ${state.cameraJoystickX * maximumDistance}px,
            ${state.cameraJoystickY * maximumDistance}px
        )`;
}

function updateCameraReadout() {
    const panPercent = Math.round(state.cameraPan * 100);

    const tiltPercent = Math.round(state.cameraTilt * 100);

    let panText = "Center";

    if (panPercent < 0) {
        panText = `Left ${Math.abs(panPercent)}%`;
    } else if (panPercent > 0) {
        panText = `Right ${panPercent}%`;
    }

    let tiltText = "Center";

    if (tiltPercent < 0) {
        tiltText = `Down ${Math.abs(tiltPercent)}%`;
    } else if (tiltPercent > 0) {
        tiltText = `Up ${tiltPercent}%`;
    }

    elements.cameraPanValue.textContent = panText;

    elements.cameraTiltValue.textContent = tiltText;
}

function updateCameraStateFromJoystick() {
    state.cameraPan = shapeAxis(
        state.cameraJoystickX,
        CAMERA_DEAD_ZONE,
        CAMERA_CURVE,
    );

    state.cameraTilt = shapeAxis(
        -state.cameraJoystickY,
        CAMERA_DEAD_ZONE,
        CAMERA_CURVE,
    );

    positionCameraStick();

    updateCameraReadout();

    sendDriveState();
}

function setCameraFromPointer(event) {
    const bounds = elements.cameraJoystick.getBoundingClientRect();

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

    state.cameraJoystickX = clamp(x, -1, 1);

    state.cameraJoystickY = clamp(y, -1, 1);

    updateCameraStateFromJoystick();
}

function releaseCameraJoystick(event) {
    if (!state.cameraJoystickActive) {
        return;
    }

    event.preventDefault();

    state.cameraJoystickActive = false;

    /*
     * Do not reset x/y. The camera remains
     * pointed at the selected position.
     */
    sendDriveState(true);
}

function configurePointerCamera() {
    elements.cameraJoystick.addEventListener("pointerdown", (event) => {
        event.preventDefault();

        state.cameraJoystickActive = true;

        elements.cameraJoystick.setPointerCapture(event.pointerId);

        setCameraFromPointer(event);
    });

    elements.cameraJoystick.addEventListener("pointermove", (event) => {
        if (!state.cameraJoystickActive) {
            return;
        }

        event.preventDefault();

        setCameraFromPointer(event);
    });

    elements.cameraJoystick.addEventListener(
        "pointerup",
        releaseCameraJoystick,
    );

    elements.cameraJoystick.addEventListener(
        "pointercancel",
        releaseCameraJoystick,
    );

    elements.cameraJoystick.addEventListener(
        "lostpointercapture",
        releaseCameraJoystick,
    );
}

function moveCameraFromKeyboard(key) {
    const step = 0.1;

    switch (key) {
        case "ArrowLeft":
            state.cameraJoystickX -= step;
            break;

        case "ArrowRight":
            state.cameraJoystickX += step;
            break;

        case "ArrowUp":
            state.cameraJoystickY -= step;
            break;

        case "ArrowDown":
            state.cameraJoystickY += step;
            break;

        default:
            return false;
    }

    state.cameraJoystickX = clamp(state.cameraJoystickX, -1, 1);

    state.cameraJoystickY = clamp(state.cameraJoystickY, -1, 1);

    updateCameraStateFromJoystick();

    return true;
}

function configureKeyboardCamera() {
    elements.cameraJoystick.addEventListener("keydown", (event) => {
        if (!moveCameraFromKeyboard(event.key)) {
            return;
        }

        event.preventDefault();
    });
}

function centerCamera() {
    state.cameraJoystickX = 0;

    state.cameraJoystickY = 0;

    state.cameraPan = 0;

    state.cameraTilt = 0;

    positionCameraStick();

    updateCameraReadout();

    sendDriveState(true);
}

export function initializeCameraControls() {
    configurePointerCamera();

    configureKeyboardCamera();

    elements.cameraCenterButton.addEventListener("click", centerCamera);

    positionCameraStick();

    updateCameraReadout();
}
