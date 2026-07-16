import {
    VideoConnection,
} from "./webrtc.js";

const HEARTBEAT_INTERVAL_MS = 500;

const DRIVE_DEAD_ZONE = 0.12;
const CAMERA_DEAD_ZONE = 0.08;

const DRIVE_THROTTLE_CURVE = 1.7;
const DRIVE_STEERING_CURVE = 1.5;
const CAMERA_CURVE = 1.6;

const STATUS_REFRESH_INTERVAL_MS = 5000;

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

    controlPaused: false,
    pageClosing: false,
};

const DRIVE_SEND_INTERVAL_MS = 50;

let lastDriveSendTime = 0;
let pendingDriveTimer = null;
let videoConnection = null;

let driveConnection = null;

const element = (id) => document.getElementById(id);

function clamp(value, minimum, maximum) {
    return Math.min(
        maximum,
        Math.max(minimum, value)
    );
}

function formatVoltage(value) {
    const voltage = Number(value);

    if (!Number.isFinite(voltage)) {
        return "--";
    }

    return `${voltage.toFixed(2)} V`;
}


function formatTemperature(value) {
    const temperature = Number(value);

    if (!Number.isFinite(temperature)) {
        return "--";
    }

    return `${temperature.toFixed(1)} °C`;
}


function setHudHealth(
    label,
    cssClass
) {
    element(
        "hud-health"
    ).textContent = label;

    const dot = element(
        "hud-health-dot"
    );

    dot.classList.remove(
        "hud-unknown",
        "hud-healthy",
        "hud-warning",
        "hud-critical"
    );

    dot.classList.add(
        cssClass
    );
}

function determineHealth(status) {
    const hardware =
        status.hardware ?? {};

    const battery =
        hardware.battery ?? {};

    const vision =
        hardware.vision ?? {};

    const systemHealth =
        status.system_health ?? {};

    const temperature =
        systemHealth.temperature ?? {};

    const throttling =
        systemHealth.throttling ?? {};

    if (
        battery.state === "critical"
        || temperature.state === "critical"
        || throttling.undervoltage_now === true
        || throttling.throttled_now === true
    ) {
        return {
            label: "Needs Attention",
            cssClass: "hud-critical",
        };
    }

    if (
        battery.available === false
        || battery.state === "low"
        || temperature.state === "high"
        || vision.service_available === false
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

function renderPlatformStatus(status) {
    const health =
        determineHealth(status);

    setHudHealth(
        health.label,
        health.cssClass
    );

    element(
        "hud-battery"
    ).textContent =
        formatVoltage(
            status.hardware
                ?.battery
                ?.voltage
        );

    element(
        "hud-temperature"
    ).textContent =
        formatTemperature(
            status.system_health
                ?.temperature
                ?.celsius
        );
}


function renderPlatformStatusError() {
    setHudHealth(
        "Unavailable",
        "hud-critical"
    );

    element(
        "hud-battery"
    ).textContent = "--";

    element(
        "hud-temperature"
    ).textContent = "--";
}


async function refreshPlatformStatus() {
    try {
        const response = await fetch(
            "/api/status",
            {
                cache: "no-store",
                headers: {
                    Accept:
                        "application/json",
                },
            }
        );

        if (!response.ok) {
            throw new Error(
                `Status request failed: `
                + response.status
            );
        }

        const status =
            await response.json();

        renderPlatformStatus(
            status
        );

    } catch (error) {
        console.error(
            "Could not load platform status",
            error
        );

        renderPlatformStatusError();
    }
}

function setVideoState(state) {
    const panel =
        document.querySelector(
            ".video-panel"
        );

    panel.dataset.videoState =
        state;

    const status =
        document.querySelector(
            ".video-status"
        );

    const labels = {
        connecting:
            "Connecting camera…",
        connected:
            "Camera connected",
        disconnected:
            "Reconnecting camera…",
        error:
            "Camera unavailable",
        closed:
            "Camera disconnected",
    };

    if (status !== null) {
        status.textContent =
            labels[state]
            ?? "Camera";
    }

    const hudCamera =
        element("hud-camera");

    if (hudCamera !== null) {
        const hudLabels = {
            connecting:
                "Connecting",
            connected:
                "Connected",
            disconnected:
                "Reconnecting",
            error:
                "Unavailable",
            closed:
                "Disconnected",
        };

        hudCamera.textContent =
            hudLabels[state]
            ?? "Unknown";
    }
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

function resetLocalControls() {
    if (
        pendingDriveTimer !== null
    ) {
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

    element(
        "drive-command"
    ).textContent = "Stopped";
}


function stopAndResetControls() {
    if (
        state.ready
        && state.websocket !== null
        && state.websocket.readyState
            === WebSocket.OPEN
    ) {
        sendJson({
            type: "stop",
        });
    }

    resetLocalControls();
}


function emergencyStop() {
    stopAndResetControls();
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

    const hudDrive =
        element("hud-drive");

    if (hudDrive !== null) {
        const hudLabels = {
            "status-connecting":
                "Connecting",
            "status-connected":
                "Connected",
            "status-busy":
                "Busy",
            "status-paused":
                "Paused",
            "status-disconnected":
                "Disconnected",
        };

        hudDrive.textContent =
            hudLabels[cssClass]
            ?? label;
    }
}

class DriveConnection {
    constructor(url) {
        this.url = url;
        this.websocket = null;
        this.heartbeatTimer = null;
        this.reconnectTimer = null;
        this.reconnectDelayMs = 750;
        this.resumeRequested = false;
    }

    connect() {
        if (
            state.pageClosing
            || document.hidden
        ) {
            return;
        }

        if (
            this.websocket !== null
            && (
                this.websocket.readyState
                    === WebSocket.OPEN
                || this.websocket.readyState
                    === WebSocket.CONNECTING
            )
        ) {
            return;
        }

        this.cancelReconnect();

        state.controlPaused = false;

        setConnectionState(
            "Connecting…",
            "status-connecting"
        );

        const websocket = new WebSocket(
            this.url
        );

        this.websocket = websocket;
        state.websocket = websocket;

        websocket.addEventListener(
            "open",
            () => {
                if (
                    websocket
                    !== this.websocket
                ) {
                    return;
                }

                setConnectionState(
                    "Requesting Control…",
                    "status-connecting"
                );
            }
        );

        websocket.addEventListener(
            "message",
            (event) => {
                this.handleMessage(
                    websocket,
                    event
                );
            }
        );

        websocket.addEventListener(
            "close",
            (event) => {
                this.handleClose(
                    websocket,
                    event
                );
            }
        );

        websocket.addEventListener(
            "error",
            () => {
                if (
                    websocket
                    !== this.websocket
                ) {
                    return;
                }

                setConnectionState(
                    "Connection Error",
                    "status-disconnected"
                );
            }
        );
    }

    handleMessage(
        websocket,
        event
    ) {
        if (
            websocket
            !== this.websocket
        ) {
            return;
        }

        let message;

        try {
            message = JSON.parse(
                event.data
            );
        } catch (error) {
            console.error(
                "Invalid websocket message",
                error
            );
            return;
        }

        if (message.type === "ready") {
            state.ready = true;
            state.controlPaused = false;

            setConnectionState(
                "Control Active",
                "status-connected"
            );

            element(
                "drive-owner"
            ).textContent =
                "You have control";

            this.startHeartbeat();
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

        if (message.type === "unavailable") {
            state.ready = false;

            setConnectionState(
                "Robot In Use",
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

            stopAndResetControls();
        }
    }

    handleClose(
        websocket,
        event
    ) {
        if (
            websocket
            !== this.websocket
        ) {
            return;
        }

        this.stopHeartbeat();

        this.websocket = null;
        state.websocket = null;
        state.ready = false;

        resetLocalControls();

        const shouldResume = (
            this.resumeRequested
            && !document.hidden
            && !state.pageClosing
        );

        this.resumeRequested = false;

        if (
            state.pageClosing
        ) {
            return;
        }

        if (shouldResume) {
            this.connect();
            return;
        }

        if (
            state.controlPaused
            || document.hidden
        ) {
            setConnectionState(
                "Control Paused",
                "status-paused"
            );

            element(
                "drive-owner"
            ).textContent =
                "Control paused while this tab is inactive.";

            return;
        }

        if (event.code === 4002) {
            setConnectionState(
                "Robot In Use",
                "status-busy"
            );

            element(
                "drive-owner"
            ).textContent =
                "The robot is currently being used "
                + "by another application.";

            return;
        }

        if (event.code === 4001) {
            setConnectionState(
                "Robot Busy",
                "status-busy"
            );

            element(
                "drive-owner"
            ).textContent =
                "The robot is already being controlled "
                + "from another browser.";

            return;
        }

        if (event.code === 4003) {
            setConnectionState(
                "Control Lost",
                "status-paused"
            );

            element(
                "drive-owner"
            ).textContent =
                "Drive control expired because "
                + "heartbeats stopped.";

            this.scheduleReconnect();
            return;
        }

        setConnectionState(
            "Disconnected",
            "status-disconnected"
        );

        element(
            "drive-owner"
        ).textContent =
            "Drive control disconnected";

        this.scheduleReconnect();
    }

    suspend() {
        if (
            state.pageClosing
            || state.controlPaused
        ) {
            return;
        }

        state.controlPaused = true;
        this.resumeRequested = false;

        stopAndResetControls();

        this.stopHeartbeat();
        this.cancelReconnect();

        const websocket =
            this.websocket;

        if (
            websocket !== null
            && websocket.readyState
                === WebSocket.OPEN
        ) {
            websocket.close(
                1000,
                "manual drive tab inactive"
            );

        } else if (
            websocket !== null
            && websocket.readyState
                === WebSocket.CONNECTING
        ) {
            websocket.close();
        }

        setConnectionState(
            "Control Paused",
            "status-paused"
        );

        element(
            "drive-owner"
        ).textContent =
            "Control paused while this tab is inactive.";
    }

    resume() {
        if (
            state.pageClosing
            || document.hidden
        ) {
            return;
        }

        state.controlPaused = false;
        this.resumeRequested = true;

        setConnectionState(
            "Reconnecting…",
            "status-connecting"
        );

        element(
            "drive-owner"
        ).textContent =
            "Requesting robot control…";

        if (
            this.websocket !== null
            && this.websocket.readyState
                === WebSocket.CLOSING
        ) {
            return;
        }

        this.resumeRequested = false;
        this.connect();
    }

    shutdown() {
        state.pageClosing = true;
        state.controlPaused = false;

        stopAndResetControls();

        this.stopHeartbeat();
        this.cancelReconnect();

        const websocket =
            this.websocket;

        state.ready = false;
        state.websocket = null;

        if (
            websocket !== null
            && (
                websocket.readyState
                    === WebSocket.OPEN
                || websocket.readyState
                    === WebSocket.CONNECTING
            )
        ) {
            websocket.close(
                1000,
                "manual drive page closed"
            );
        }
    }

    startHeartbeat() {
        this.stopHeartbeat();

        this.heartbeatTimer =
            window.setInterval(
                () => {
                    if (
                        state.ready
                        && !document.hidden
                    ) {
                        sendJson({
                            type: "heartbeat",
                        });
                    }
                },
                HEARTBEAT_INTERVAL_MS
            );
    }

    stopHeartbeat() {
        if (
            this.heartbeatTimer
            === null
        ) {
            return;
        }

        window.clearInterval(
            this.heartbeatTimer
        );

        this.heartbeatTimer = null;
    }

    scheduleReconnect() {
        if (
            state.pageClosing
            || state.controlPaused
            || document.hidden
            || this.reconnectTimer !== null
        ) {
            return;
        }

        this.reconnectTimer =
            window.setTimeout(
                () => {
                    this.reconnectTimer = null;
                    this.connect();
                },
                this.reconnectDelayMs
            );
    }

    cancelReconnect() {
        if (
            this.reconnectTimer
            === null
        ) {
            return;
        }

        window.clearTimeout(
            this.reconnectTimer
        );

        this.reconnectTimer = null;
    }
}

class ManualDriveSession {
    constructor() {
        this.driveConnection = null;
        this.videoConnection = null;
        this.statusTimer = null;
        this.started = false;
    }

    start() {
        if (this.started) {
            return;
        }

        this.started = true;

        this.configureControls();
        this.initializeInterface();
        this.initializeVideo();
        this.initializeDriveConnection();
        this.configureLifecycle();
        this.startStatusRefresh();
    }

    configureControls() {
        configureKeyboard();
        configureCameraJoystick();
        configureJoystick();
        configureSpeed();
        configureSafety();
    }

    initializeInterface() {
        updateCameraReadout();
        updateJoystickReadout();
        positionDriveStick();
        positionCameraStick();
    }

    initializeVideo() {
        this.videoConnection =
            new VideoConnection(
                element("drive-video"),
                "/api/vision/offer",
                {
                    onStateChange:
                        setVideoState,
                }
            );

        videoConnection =
            this.videoConnection;

        this.videoConnection.connect();
    }

    initializeDriveConnection() {
        const scheme =
            window.location.protocol
                === "https:"
                ? "wss"
                : "ws";

        const url =
            `${scheme}://`
            + `${window.location.host}`
            + "/ws/drive";

        this.driveConnection =
            new DriveConnection(
                url
            );

        driveConnection =
            this.driveConnection;

        this.driveConnection.connect();
    }

    startStatusRefresh() {
        refreshPlatformStatus();

        this.statusTimer =
            window.setInterval(
                refreshPlatformStatus,
                STATUS_REFRESH_INTERVAL_MS
            );
    }

    stopStatusRefresh() {
        if (
            this.statusTimer === null
        ) {
            return;
        }

        window.clearInterval(
            this.statusTimer
        );

        this.statusTimer = null;
    }

    suspend() {
        if (!this.started) {
            return;
        }

        this.driveConnection?.suspend();
    }

    resume() {
        if (
            !this.started
            || document.hidden
            || state.pageClosing
        ) {
            return;
        }

        this.driveConnection?.resume();

        void refreshPlatformStatus();
    }

    stopMotion() {
        stopAndResetControls();
    }

    shutdown() {
        if (!this.started) {
            return;
        }

        this.started = false;

        this.stopStatusRefresh();

        this.driveConnection?.shutdown();

        if (this.videoConnection !== null) {
            void this.videoConnection.close();
        }
    }

    configureLifecycle() {
        document.addEventListener(
            "visibilitychange",
            () => {
                if (document.hidden) {
                    this.suspend();
                    return;
                }

                this.resume();
            }
        );

        window.addEventListener(
            "blur",
            () => {
                this.stopMotion();
            }
        );

        window.addEventListener(
            "pagehide",
            () => {
                this.shutdown();
            }
        );

        window.addEventListener(
            "beforeunload",
            () => {
                this.shutdown();
            }
        );
    }
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
}

let manualDriveSession = null;


document.addEventListener(
    "DOMContentLoaded",
    () => {
        manualDriveSession =
            new ManualDriveSession();

        manualDriveSession.start();
    }
);
