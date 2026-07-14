"use strict";

const HEARTBEAT_INTERVAL_MS = 500;
const JOYSTICK_DEAD_ZONE = 0.12;

const state = {
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
};

const DRIVE_SEND_INTERVAL_MS = 50;

let lastDriveSendTime = 0;
let pendingDriveTimer = null;

const element = (id) => document.getElementById(id);

function clamp(value, minimum, maximum) {
    return Math.min(
        maximum,
        Math.max(minimum, value)
    );
}

function applyDeadZone(value) {
    if (Math.abs(value) < JOYSTICK_DEAD_ZONE) {
        return 0;
    }

    const direction = Math.sign(value);
    const adjusted =
        (Math.abs(value) - JOYSTICK_DEAD_ZONE) /
        (1 - JOYSTICK_DEAD_ZONE);

    return direction * adjusted;
}

function effectiveThrottle() {
    if (state.joystickActive) {
        return applyDeadZone(
            -state.joystickY
        );
    }

    if (
        state.keyboardForward &&
        !state.keyboardBackward
    ) {
        return 1;
    }

    if (
        state.keyboardBackward &&
        !state.keyboardForward
    ) {
        return -1;
    }

    return 0;
}

function effectiveSteering() {
    if (state.joystickActive) {
        return applyDeadZone(
            state.joystickX
        );
    }

    if (
        state.keyboardLeft &&
        !state.keyboardRight
    ) {
        return -1;
    }

    if (
        state.keyboardRight &&
        !state.keyboardLeft
    ) {
        return 1;
    }

    return 0;
}


function sendJson(message) {
    if (
        !state.websocket ||
        state.websocket.readyState !== WebSocket.OPEN
    ) {
        return false;
    }

    state.websocket.send(
        JSON.stringify(message)
    );

    return true;
}

function describeControlState(
    throttle,
    steering
) {
    const throttlePercent = Math.round(
        Math.abs(throttle) * 100
    );

    let motionText = "Stopped";

    if (throttle > 0) {
        motionText =
            `Forward ${throttlePercent}%`;
    } else if (throttle < 0) {
        motionText =
            `Reverse ${throttlePercent}%`;
    }

    if (steering < 0) {
        return `${motionText} · Left`;
    }

    if (steering > 0) {
        return `${motionText} · Right`;
    }

    return motionText;
}


function sendDriveState(
    force = false
) {
    if (!state.ready) {
        return;
    }

    const now = performance.now();
    const elapsed =
        now - lastDriveSendTime;

    if (
        !force &&
        elapsed < DRIVE_SEND_INTERVAL_MS
    ) {
        if (pendingDriveTimer === null) {
            pendingDriveTimer =
                window.setTimeout(
                    () => {
                        pendingDriveTimer = null;
                        sendDriveState(true);
                    },
                    DRIVE_SEND_INTERVAL_MS
                        - elapsed
                );
        }

        return;
    }

    lastDriveSendTime = now;

    const maximumThrottle =
        state.speed / 100;

    const throttle =
        effectiveThrottle()
        * maximumThrottle;

    const steering =
        effectiveSteering();

    const controlState = {
        throttle,
        steering,
        camera_pan: state.cameraPan,
        camera_tilt: state.cameraTilt,
        headlights: state.headlights,
        horn: state.horn,
    };

    const serialized =
        JSON.stringify(controlState);

    if (
        !force &&
        serialized === state.lastCommand
    ) {
        return;
    }

    state.lastCommand = serialized;

    sendJson({
        type: "control",
        ...controlState,
    });

    element(
        "drive-command"
    ).textContent =
        describeControlState(
            throttle,
            steering
        );
}

function emergencyStop() {
    if (pendingDriveTimer !== null) {
        window.clearTimeout(
            pendingDriveTimer
        );

        pendingDriveTimer = null;
    }

    state.keyboardForward = false;
    state.keyboardBackward = false;
    state.keyboardLeft = false;
    state.keyboardRight = false;

    resetJoystick(false);

    state.lastCommand = "";

    sendJson({
        type: "stop",
    });

    element("drive-command").textContent =
        "Stopped";
}

function setConnectionState(
    label,
    cssClass
) {
    const connection = element(
        "drive-connection"
    );

    connection.className =
        `drive-connection ${cssClass}`;

    connection.textContent = label;
}

function connect() {
    const scheme =
        window.location.protocol === "https:"
            ? "wss"
            : "ws";

    const url =
        `${scheme}://${window.location.host}/ws/drive`;

    setConnectionState(
        "Connecting…",
        "status-connecting"
    );

    const websocket = new WebSocket(url);
    state.websocket = websocket;

    websocket.addEventListener(
        "open",
        () => {
            setConnectionState(
                "Requesting Control…",
                "status-connecting"
            );
        }
    );

    websocket.addEventListener(
        "message",
        (event) => {
            const message = JSON.parse(
                event.data
            );

            if (message.type === "ready") {
                state.ready = true;

                setConnectionState(
                    "Control Active",
                    "status-connected"
                );

                element(
                    "drive-owner"
                ).textContent =
                    "You have control";

                sendDriveState(true);
                return;
            }

            if (message.type === "busy") {
                state.ready = false;

                setConnectionState(
                    "Robot Busy",
                    "status-busy"
                );

                element(
                    "drive-owner"
                ).textContent =
                    message.message;

                return;
            }

            if (message.type === "error") {
                console.error(
                    message.message
                );

                emergencyStop();
            }
        }
    );

    websocket.addEventListener(
        "close",
        () => {
            state.ready = false;
            state.websocket = null;

            emergencyStop();

            setConnectionState(
                "Disconnected",
                "status-disconnected"
            );

            element(
                "drive-owner"
            ).textContent =
                "Drive control disconnected";
        }
    );

    websocket.addEventListener(
        "error",
        () => {
            setConnectionState(
                "Connection Error",
                "status-disconnected"
            );
        }
    );
}

function heartbeat() {
    if (!state.ready) {
        return;
    }

    sendJson({
        type: "heartbeat",
    });
}

function keyboardControlForKey(key) {
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

function configureKeyboard() {
    window.addEventListener(
        "keydown",
        (event) => {
            if (
                event.target instanceof HTMLInputElement
            ) {
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

            const control =
                keyboardControlForKey(
                    event.key
                );

            if (!control) {
                return;
            }

            event.preventDefault();
            state[control] = true;
            sendDriveState();
        }
    );

    window.addEventListener(
        "keyup",
        (event) => {
            const control =
                keyboardControlForKey(
                    event.key
                );

            if (!control) {
                return;
            }

            event.preventDefault();
            state[control] = false;
            sendDriveState();
        }
    );
}

function updateJoystickReadout() {
  const throttle =
      effectiveThrottle()
      * (state.speed / 100);
    const steering = effectiveSteering();

    element(
        "throttle-value"
    ).textContent =
        `${Math.round(throttle * 100)}%`;

    let steeringText = "Center";

    if (steering < 0) {
        steeringText =
            `Left ${Math.round(
                Math.abs(steering) * 100
            )}%`;
    } else if (steering > 0) {
        steeringText =
            `Right ${Math.round(
                steering * 100
            )}%`;
    }

    element(
        "steering-value"
    ).textContent = steeringText;
}

function positionJoystickStick() {
    const joystick = element(
        "drive-joystick"
    );

    const stick = element(
        "drive-stick"
    );

    const bounds =
        joystick.getBoundingClientRect();

    const maximumDistance =
        bounds.width * 0.34;

    stick.style.transform =
        `translate(
            ${state.joystickX * maximumDistance}px,
            ${state.joystickY * maximumDistance}px
        )`;
}

function setJoystickFromPointer(
    event
) {
    const joystick = element(
        "drive-joystick"
    );

    const bounds =
        joystick.getBoundingClientRect();

    const centerX =
        bounds.left + bounds.width / 2;

    const centerY =
        bounds.top + bounds.height / 2;

    const radius =
        Math.min(
            bounds.width,
            bounds.height
        ) / 2;

    let x =
        (event.clientX - centerX) /
        radius;

    let y =
        (event.clientY - centerY) /
        radius;

    const magnitude =
        Math.hypot(x, y);

    if (magnitude > 1) {
        x /= magnitude;
        y /= magnitude;
    }

    state.joystickX =
        clamp(x, -1, 1);

    state.joystickY =
        clamp(y, -1, 1);

    positionJoystickStick();
    updateJoystickReadout();
    sendDriveState();
}

function resetJoystick(
    sendCommand = true
) {
    state.joystickActive = false;
    state.joystickX = 0;
    state.joystickY = 0;

    positionJoystickStick();
    updateJoystickReadout();

    if (sendCommand) {
        sendDriveState(true);
    }
}

function configureJoystick() {
    const joystick = element(
        "drive-joystick"
    );

    joystick.addEventListener(
        "pointerdown",
        (event) => {
            event.preventDefault();

            state.joystickActive = true;

            joystick.setPointerCapture(
                event.pointerId
            );

            setJoystickFromPointer(
                event
            );
        }
    );

    joystick.addEventListener(
        "pointermove",
        (event) => {
            if (!state.joystickActive) {
                return;
            }

            event.preventDefault();

            setJoystickFromPointer(
                event
            );
        }
    );

    const release = (event) => {
        if (!state.joystickActive) {
            return;
        }

        event.preventDefault();
        resetJoystick();
    };

    joystick.addEventListener(
        "pointerup",
        release
    );

    joystick.addEventListener(
        "pointercancel",
        release
    );

    joystick.addEventListener(
        "lostpointercapture",
        release
    );
}

function configureSpeed() {
    const input = element("speed");

    input.addEventListener(
        "input",
        () => {
            state.speed = Number(
                input.value
            );

            element(
                "speed-value"
            ).textContent =
                `${state.speed}%`;

            sendDriveState(true);
        }
    );
}

function configureSafety() {
    element(
        "emergency-stop"
    ).addEventListener(
        "click",
        emergencyStop
    );

    document.addEventListener(
        "visibilitychange",
        () => {
            if (document.hidden) {
                emergencyStop();
            }
        }
    );

    window.addEventListener(
        "blur",
        emergencyStop
    );

    window.addEventListener(
        "beforeunload",
        emergencyStop
    );
}

document.addEventListener(
    "DOMContentLoaded",
    () => {
        configureKeyboard();
        configureJoystick();
        configureSpeed();
        configureSafety();

        updateJoystickReadout();
        positionJoystickStick();

        connect();

        window.setInterval(
            heartbeat,
            HEARTBEAT_INTERVAL_MS
        );
    }
);
