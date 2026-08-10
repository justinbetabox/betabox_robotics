"use strict";

function requireElement(selector, expectedType = HTMLElement) {
    const element = document.querySelector(selector);

    if (!(element instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return element;
}

export const elements = {
    videoPanel: requireElement(".video-panel"),

    videoStatus: requireElement(".video-status"),

    video: requireElement("#drive-video", HTMLVideoElement),

    healthDot: requireElement("#hud-health-dot"),

    health: requireElement("#hud-health"),

    battery: requireElement("#hud-battery"),

    temperature: requireElement("#hud-temperature"),

    driveStatus: requireElement("#hud-drive"),

    cameraStatus: requireElement("#hud-camera"),

    owner: requireElement("#drive-owner"),

    command: requireElement("#drive-command"),

    connection: requireElement("#drive-connection"),

    speed: requireElement("#speed", HTMLInputElement),

    speedValue: requireElement("#speed-value"),

    driveJoystick: requireElement("#drive-joystick"),

    driveStick: requireElement("#drive-stick"),

    throttleValue: requireElement("#throttle-value"),

    steeringValue: requireElement("#steering-value"),

    cameraJoystick: requireElement("#camera-joystick"),

    cameraStick: requireElement("#camera-stick"),

    cameraPanValue: requireElement("#camera-pan-value"),

    cameraTiltValue: requireElement("#camera-tilt-value"),

    cameraCenterButton: requireElement("#camera-center", HTMLButtonElement),

    emergencyStopButton: requireElement("#emergency-stop", HTMLButtonElement),
};
