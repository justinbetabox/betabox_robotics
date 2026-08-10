"use strict";

export const state = {
    websocket: null,
    ready: false,
    speed: 40,

    keyboardForward: false,
    keyboardBackward: false,
    keyboardLeft: false,
    keyboardRight: false,

    joystickActive: false,
    joystickX: 0,
    joystickY: 0,

    lastCommand: "",

    cameraPan: 0,
    cameraTilt: 0,
    headlights: false,
    horn: false,

    cameraJoystickActive: false,
    cameraJoystickX: 0,
    cameraJoystickY: 0,

    controlPaused: false,
    pageClosing: false,

    lastDriveSendTime: 0,
    pendingDriveTimer: null,
};
