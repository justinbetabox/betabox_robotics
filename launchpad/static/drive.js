import {
    VideoConnection,
} from "./webrtc.js";

const HEARTBEAT_INTERVAL_MS = 500;

const DRIVE_DEAD_ZONE = 0.12;
const CAMERA_DEAD_ZONE = 0.08;

const DRIVE_THROTTLE_CURVE = 1.7;
const DRIVE_STEERING_CURVE = 1.5;
const CAMERA_CURVE = 1.6;

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

    cameraJoystickActive: false,
    cameraJoystickX: 0,
    cameraJoystickY: 0,
};

const DRIVE_SEND_INTERVAL_MS = 50;

let lastDriveSendTime = 0;
let pendingDriveTimer = null;
let videoConnection = null;

const element = (id) => document.getElementById(id);

function clamp(value, minimum, maximum) {
    return Math.min(
        maximum,
        Math.max(minimum, value)
    );
}

function setVideoState(state) {
    const panel = document.querySelector(
        ".video-panel"
    );

    panel.dataset.videoState = state;

    const status = document.querySelector(
        ".video-status"
    );

    if (!status) {
        return;
    }

    const labels = {
        connecting: "Connecting camera…",
        connected: "Camera connected",
        disconnected: "Reconnecting camera…",
        error: "Camera unavailable",
        closed: "Camera disconnected",
    };

    status.textContent =
        labels[state] ?? "Camera";
}

function shapeAxis(
    value,
    deadZone,
    exponent
) {
    const magnitude = Math.abs(value);

    if (magnitude <= deadZone) {
        return 0;
    }

    const normalized =
        (magnitude - deadZone)
        / (1 - deadZone);

    const curved =
        Math.pow(
            normalized,
            exponent
        );

    return Math.sign(value) * curved;
}

function effectiveThrottle() {
    let raw = 0;

    if (state.joystickActive) {
        raw = -state.joystickY;
    } else if (
        state.keyboardForward &&
        !state.keyboardBackward
    ) {
        raw = 1;
    } else if (
        state.keyboardBackward &&
        !state.keyboardForward
    ) {
        raw = -1;
    }

    return shapeAxis(
        raw,
        DRIVE_DEAD_ZONE,
        DRIVE_THROTTLE_CURVE
    );
}


function effectiveSteering() {
    let raw = 0;

    if (state.joystickActive) {
        raw = state.joystickX;
    } else if (
        state.keyboardLeft &&
        !state.keyboardRight
    ) {
        raw = -1;
    } else if (
        state.keyboardRight &&
        !state.keyboardLeft
    ) {
        raw = 1;
    }

    return shapeAxis(
        raw,
        DRIVE_DEAD_ZONE,
        DRIVE_STEERING_CURVE
    );
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

function updateCameraReadout() {
    const panPercent =
        Math.round(
            state.cameraPan * 100
        );

    const tiltPercent =
        Math.round(
            state.cameraTilt * 100
        );

    let panText = "Center";

    if (panPercent < 0) {
        panText =
            `Left ${Math.abs(panPercent)}%`;
    } else if (panPercent > 0) {
        panText =
            `Right ${panPercent}%`;
    }

    let tiltText = "Center";

    if (tiltPercent < 0) {
        tiltText =
            `Down ${Math.abs(tiltPercent)}%`;
    } else if (tiltPercent > 0) {
        tiltText =
            `Up ${tiltPercent}%`;
    }

    element(
        "camera-pan-value"
    ).textContent = panText;

    element(
        "camera-tilt-value"
    ).textContent = tiltText;
}

function sendDriveState(
    force = false
) {
    if (!state.ready) {
        return;
    }

    if (
        force &&
        pendingDriveTimer !== null
    ) {
        window.clearTimeout(
            pendingDriveTimer
        );

        pendingDriveTimer = null;
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
            let message;

            try {
                message = JSON.parse(event.data);
            } catch (error) {
                console.error(
                    "Invalid websocket message",
                    error
                );
                return;
            }

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

            if (message.type === "accepted") {
                return;
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

function positionStick(
    joystickId,
    stickId,
    x,
    y
) {
    const joystick = element(
        joystickId
    );

    const stick = element(
        stickId
    );

    const bounds =
        joystick.getBoundingClientRect();

    const maximumDistance =
        bounds.width * 0.34;

    stick.style.transform =
        `translate(
            ${x * maximumDistance}px,
            ${y * maximumDistance}px
        )`;
}


function positionDriveStick() {
    positionStick(
        "drive-joystick",
        "drive-stick",
        state.joystickX,
        state.joystickY
    );
}


function positionCameraStick() {
    positionStick(
        "camera-joystick",
        "camera-stick",
        state.cameraJoystickX,
        state.cameraJoystickY
    );
}

function setCameraFromPointer(
    event
) {
    const joystick = element(
        "camera-joystick"
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
        (event.clientX - centerX)
        / radius;

    let y =
        (event.clientY - centerY)
        / radius;

    const magnitude =
        Math.hypot(x, y);

    if (magnitude > 1) {
        x /= magnitude;
        y /= magnitude;
    }

    state.cameraJoystickX =
        clamp(x, -1, 1);

    state.cameraJoystickY =
        clamp(y, -1, 1);

    state.cameraPan = shapeAxis(
        state.cameraJoystickX,
        CAMERA_DEAD_ZONE,
        CAMERA_CURVE
    );

    state.cameraTilt = shapeAxis(
        -state.cameraJoystickY,
        CAMERA_DEAD_ZONE,
        CAMERA_CURVE
    );

    positionCameraStick();
    updateCameraReadout();
    sendDriveState();
}

function configureCameraJoystick() {
    const joystick = element(
        "camera-joystick"
    );

    joystick.addEventListener(
        "pointerdown",
        (event) => {
            event.preventDefault();

            state.cameraJoystickActive = true;

            joystick.setPointerCapture(
                event.pointerId
            );

            setCameraFromPointer(
                event
            );
        }
    );

    joystick.addEventListener(
        "pointermove",
        (event) => {
            if (!state.cameraJoystickActive) {
                return;
            }

            event.preventDefault();

            setCameraFromPointer(
                event
            );
        }
    );

    const release = (event) => {
        if (!state.cameraJoystickActive) {
            return;
        }

        event.preventDefault();

        state.cameraJoystickActive = false;

        // Do not reset x/y. The camera remains pointed
        // at the selected position.
        sendDriveState(true);
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

    element(
        "camera-center"
    ).addEventListener(
        "click",
        () => {
            state.cameraJoystickX = 0;
            state.cameraJoystickY = 0;
            state.cameraPan = 0;
            state.cameraTilt = 0;

            positionCameraStick();
            updateCameraReadout();
            sendDriveState(true);
        }
    );
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

    positionDriveStick();
    updateJoystickReadout();
    sendDriveState();
}

function resetJoystick(
    sendCommand = true
) {
    state.joystickActive = false;
    state.joystickX = 0;
    state.joystickY = 0;

    positionDriveStick();
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
          () => {
              emergencyStop();

              if (
                  videoConnection !== null
              ) {
                  void videoConnection.close();
              }
          }
    );
}

document.addEventListener(
    "DOMContentLoaded",
    () => {
        configureKeyboard();
        configureCameraJoystick();
        configureJoystick();
        configureSpeed();
        configureSafety();
        updateCameraReadout();

        updateJoystickReadout();
        positionDriveStick();
        positionCameraStick();

        videoConnection =
            new VideoConnection(
                element("drive-video"),
                "/api/vision/offer",
                {
                    onStateChange:
                        setVideoState,
                }
            );

        videoConnection.connect();

        connect();

        window.setInterval(
            heartbeat,
            HEARTBEAT_INTERVAL_MS
        );
    }
);
