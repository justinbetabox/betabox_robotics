const connectionStatus = document.getElementById(
    "calibration-connection"
);

const refreshButton = document.getElementById(
    "refresh-calibration"
);

const retryButton = document.getElementById(
    "retry-calibration"
);

const loadingPanel = document.getElementById(
    "calibration-loading"
);

const contentPanel = document.getElementById(
    "calibration-content"
);

const errorPanel = document.getElementById(
    "calibration-error"
);

const errorMessage = document.getElementById(
    "calibration-error-message"
);

const sourceBadge = document.getElementById(
    "calibration-source"
);

const updatedTime = document.getElementById(
    "calibration-updated"
);

const announcement = document.getElementById(
    "calibration-announcement"
);

const steeringOffset = document.getElementById(
    "steering-offset"
);

const cameraPanOffset = document.getElementById(
    "camera-pan-offset"
);

const cameraTiltOffset = document.getElementById(
    "camera-tilt-offset"
);

const cameraStatus = document.getElementById(
    "camera-status"
);

const leftMotorTrim = document.getElementById(
    "left-motor-trim"
);

const rightMotorTrim = document.getElementById(
    "right-motor-trim"
);

const steeringStatus = document.getElementById(
    "steering-status"
);

const motorsStatus = document.getElementById(
    "motors-status"
);

const grayscaleStatus = document.getElementById(
    "grayscale-status"
);

const grayscaleFloor = document.getElementById(
    "grayscale-floor"
);

const grayscaleLine = document.getElementById(
    "grayscale-line"
);

const steeringIncreaseButton = document.getElementById(
    "steering-increase"
);

const steeringDecreaseButton = document.getElementById(
    "steering-decrease"
);

const steeringSaveButton = document.getElementById(
    "steering-save"
);

const steeringResetButton = document.getElementById(
    "steering-reset"
);

const steeringMessage = document.getElementById(
    "steering-message"
);

const cameraPanIncreaseButton = document.getElementById(
    "camera-pan-increase"
);

const cameraPanDecreaseButton = document.getElementById(
    "camera-pan-decrease"
);

const cameraTiltIncreaseButton = document.getElementById(
    "camera-tilt-increase"
);

const cameraTiltDecreaseButton = document.getElementById(
    "camera-tilt-decrease"
);

const cameraSaveButton = document.getElementById(
    "camera-save"
);

const cameraResetButton = document.getElementById(
    "camera-reset"
);

const cameraMessage = document.getElementById(
    "camera-message"
);

const leftTrimIncreaseButton = document.getElementById(
    "left-trim-increase"
);

const leftTrimDecreaseButton = document.getElementById(
    "left-trim-decrease"
);

const rightTrimIncreaseButton = document.getElementById(
    "right-trim-increase"
);

const rightTrimDecreaseButton = document.getElementById(
    "right-trim-decrease"
);

const motorsSaveButton = document.getElementById(
    "motors-save"
);

const motorsResetButton = document.getElementById(
    "motors-reset"
);

const motorsPreviewButton = document.getElementById(
    "motors-preview"
);

const motorsMessage = document.getElementById(
    "motors-message"
);

const grayscaleCaptureFloorButton =
    document.getElementById(
        "grayscale-capture-floor"
    );

const grayscaleCaptureLineButton =
    document.getElementById(
        "grayscale-capture-line"
    );

const grayscaleSaveButton =
    document.getElementById(
        "grayscale-save"
    );

const grayscaleResetButton =
    document.getElementById(
        "grayscale-reset"
    );

const grayscaleClearButton =
    document.getElementById(
        "grayscale-clear"
    );

const grayscaleMessage =
    document.getElementById(
        "grayscale-message"
    );

const STEERING_STEP = 1;
const STEERING_MIN = -30;
const STEERING_MAX = 30;

const CAMERA_OFFSET_STEP = 1;
const CAMERA_OFFSET_MIN = -30;
const CAMERA_OFFSET_MAX = 30;

const MOTOR_TRIM_STEP = 0.01;
const MOTOR_TRIM_MIN = 0;
const MOTOR_TRIM_MAX = 1;

let leftTrimValue = 1;
let rightTrimValue = 1;

let savedLeftTrim = 1;
let savedRightTrim = 1;

let cameraPanOffsetValue = 0;
let cameraTiltOffsetValue = 0;

let savedCameraPanOffset = 0;
let savedCameraTiltOffset = 0;

let steeringOffsetValue = 0;
let savedSteeringOffset = 0;

let savedGrayscaleFloor = null;
let savedGrayscaleLine = null;

let grayscaleFloorValue = null;
let grayscaleLineValue = null;

let grayscaleCalibratedValue = false;

let steeringPreviewTimer = null;
let cameraPreviewTimer = null;


function clamp(
    value,
    minimum,
    maximum,
) {
    return Math.min(
        maximum,
        Math.max(
            minimum,
            value,
        ),
    );
}


function formatOffset(
    value,
) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "—";
    }

    const prefix = number > 0
        ? "+"
        : "";

    return `${prefix}${number.toFixed(1)}°`;
}


function formatTrim(
    value,
) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "—";
    }

    return number.toFixed(2);
}


function setConnectionState(
    state,
    message,
) {
    connectionStatus.className = (
        `connection-status status-${state}`
    );

    connectionStatus.textContent = message;
}


function setBadge(
    element,
    text,
    tone,
) {
    element.className = (
        tone === "neutral"
            ? "status-badge"
            : `status-badge status-${tone}`
    );

    element.textContent = text;
}


function showLoading() {
    loadingPanel.hidden = false;
    contentPanel.hidden = true;
    errorPanel.hidden = true;

    refreshButton.disabled = true;

    setSteeringControlsDisabled(
        true
    );
    setCameraControlsDisabled(
        true
    );
    setMotorControlsDisabled(
        true
    );
    setGrayscaleControlsDisabled(
        true
    );

    setConnectionState(
        "connecting",
        "Loading…",
    );
}

function showTemporaryMessage(
    element,
    message,
    stillCurrent,
) {
    element.textContent = message;

    window.setTimeout(
        () => {
            if (stillCurrent()) {
                element.textContent = "";
            }
        },
        3000,
    );
}

function showError(
    message,
) {
    loadingPanel.hidden = true;
    contentPanel.hidden = true;
    errorPanel.hidden = false;

    refreshButton.disabled = false;

    errorMessage.textContent = message;

    setConnectionState(
        "error",
        "Unavailable",
    );

    announcement.textContent = (
        "Calibration could not be loaded."
    );
}


function restorePreviewState() {
    restoreSavedSteering();
    restoreSavedCameraMount();
}


/* Steering */

function renderSteering(
    steering,
) {
    const offset = Number(
        steering.offset
    );

    const validOffset = Number.isFinite(
        offset
    )
        ? offset
        : 0;

    savedSteeringOffset = validOffset;
    steeringOffsetValue = validOffset;

    renderSteeringEditor();

    const adjusted = (
        validOffset !== 0
    );

    setBadge(
        steeringStatus,
        adjusted
            ? "Adjusted"
            : "Default",
        adjusted
            ? "healthy"
            : "neutral",
    );
}


function renderSteeringEditor() {
    steeringOffset.textContent = formatOffset(
        steeringOffsetValue
    );

    const changed = (
        steeringOffsetValue
        !== savedSteeringOffset
    );

    steeringSaveButton.disabled = !changed;
    steeringResetButton.disabled = !changed;

    steeringMessage.textContent = (
        changed
            ? "Unsaved steering changes."
            : ""
    );
}


async function previewSteering() {
    const response = await fetch(
        "/api/calibration/steering/preview",
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json",
                Accept:
                    "application/json",
            },

            body: JSON.stringify({
                offset:
                    steeringOffsetValue,
            }),
        },
    );

    let payload;

    try {
        payload = await response.json();
    } catch {
        throw new Error(
            "Steering API returned an "
            + "invalid response."
        );
    }

    if (!response.ok) {
        throw new Error(
            payload.message
            ?? "Unable to move steering."
        );
    }
}

function scheduleSteeringPreview() {
    if (steeringPreviewTimer !== null) {
        window.clearTimeout(
            steeringPreviewTimer
        );
    }

    steeringPreviewTimer = window.setTimeout(
        async () => {
            steeringPreviewTimer = null;

            setSteeringControlsDisabled(
                true
            );

            try {
                await previewSteering();
            } catch (error) {
                steeringMessage.textContent = (
                    error instanceof Error
                        ? error.message
                        : "Unable to move steering."
                );
            } finally {
                setSteeringControlsDisabled(
                    false
                );

                renderSteeringEditor();
            }
        },
        75,
    );
}


async function saveSteering() {
    steeringSaveButton.disabled = true;
    steeringResetButton.disabled = true;
    refreshButton.disabled = true;

    steeringMessage.textContent =
        "Saving…";

    try {
        const response = await fetch(
            "/api/calibration/steering",
            {
                method: "PUT",

                headers: {
                    "Content-Type":
                        "application/json",
                    Accept:
                        "application/json",
                },

                body: JSON.stringify({
                    offset:
                        steeringOffsetValue,
                }),
            },
        );

        let payload;

        try {
            payload = await response.json();
        } catch {
            throw new Error(
                "Calibration API returned an "
                + "invalid response."
            );
        }

        if (!response.ok) {
            throw new Error(
                payload.message
                ?? (
                    "Unable to save steering "
                    + "calibration."
                )
            );
        }

        renderCalibration(
            payload
        );

        showTemporaryMessage(
            steeringMessage,
            "Steering calibration saved.",
            () => (
                steeringOffsetValue
                === savedSteeringOffset
            ),
        );

        announcement.textContent = (
            "Steering calibration saved."
        );
    } catch (error) {
        renderSteeringEditor();

        steeringMessage.textContent = (
            error instanceof Error
                ? error.message
                : (
                    "Unable to save steering "
                    + "calibration."
                )
        );
    } finally {
        refreshButton.disabled = false;
    }
}


function restoreSavedSteering() {
    if (steeringPreviewTimer !== null) {
        window.clearTimeout(
            steeringPreviewTimer
        );

        steeringPreviewTimer = null;
    }

    if (
        steeringOffsetValue
        === savedSteeringOffset
    ) {
        return;
    }

    fetch(
        "/api/calibration/steering/preview",
        {
            method: "POST",
            keepalive: true,

            headers: {
                "Content-Type":
                    "application/json",
                Accept:
                    "application/json",
            },

            body: JSON.stringify({
                offset:
                    savedSteeringOffset,
            }),
        },
    ).catch(
        () => {
            // The page is leaving, so there is
            // nowhere useful to display an error.
        },
    );
}


function setSteeringControlsDisabled(
    disabled,
) {
    steeringIncreaseButton.disabled = disabled;
    steeringDecreaseButton.disabled = disabled;

    if (disabled) {
        steeringSaveButton.disabled = true;
        steeringResetButton.disabled = true;
    }
}


/* Motors */

function renderMotors(
    motors,
) {
    const left = Number(
        motors.left_trim
    );

    const right = Number(
        motors.right_trim
    );

    const validLeft = Number.isFinite(
        left
    )
        ? left
        : 1;

    const validRight = Number.isFinite(
        right
    )
        ? right
        : 1;

    savedLeftTrim = validLeft;
    savedRightTrim = validRight;

    leftTrimValue = validLeft;
    rightTrimValue = validRight;

    renderMotorEditor();

    const adjusted = (
        validLeft !== 1
        || validRight !== 1
    );

    setBadge(
        motorsStatus,
        adjusted
            ? "Adjusted"
            : "Default",
        adjusted
            ? "healthy"
            : "neutral",
    );
}


function renderMotorEditor() {
    leftMotorTrim.textContent = formatTrim(
        leftTrimValue
    );

    rightMotorTrim.textContent = formatTrim(
        rightTrimValue
    );

    const changed = (
        leftTrimValue !== savedLeftTrim
        || rightTrimValue !== savedRightTrim
    );

    motorsSaveButton.disabled = !changed;
    motorsResetButton.disabled = !changed;

    motorsMessage.textContent = (
        changed
            ? "Unsaved motor trim changes."
            : ""
    );
}


async function previewMotorTrim() {
    const response = await fetch(
        "/api/calibration/motors/preview",
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json",
                Accept:
                    "application/json",
            },

            body: JSON.stringify({
                left_trim:
                    leftTrimValue,
                right_trim:
                    rightTrimValue,
            }),
        },
    );

    let payload;

    try {
        payload = await response.json();
    } catch {
        throw new Error(
            "Motor trim API returned an "
            + "invalid response."
        );
    }

    if (!response.ok) {
        throw new Error(
            payload.message
            ?? "Unable to preview motor trim."
        );
    }
}


async function runMotorPreview() {
    setMotorControlsDisabled(
        true
    );

    refreshButton.disabled = true;

    motorsMessage.textContent =
        "Previewing motor trim…";

    try {
        await previewMotorTrim();
    } catch (error) {
        motorsMessage.textContent = (
            error instanceof Error
                ? error.message
                : "Unable to preview motor trim."
        );
    } finally {
        setMotorControlsDisabled(
            false
        );

        refreshButton.disabled = false;

        renderMotorEditor();
    }
}


async function saveMotors() {
    motorsSaveButton.disabled = true;
    motorsResetButton.disabled = true;
    refreshButton.disabled = true;

    motorsMessage.textContent =
        "Saving…";

    try {
        const response = await fetch(
            "/api/calibration/motors",
            {
                method: "PUT",

                headers: {
                    "Content-Type":
                        "application/json",
                    Accept:
                        "application/json",
                },

                body: JSON.stringify({
                    left_trim:
                        leftTrimValue,
                    right_trim:
                        rightTrimValue,
                }),
            },
        );

        let payload;

        try {
            payload = await response.json();
        } catch {
            throw new Error(
                "Calibration API returned an "
                + "invalid response."
            );
        }

        if (!response.ok) {
            throw new Error(
                payload.message
                ?? (
                    "Unable to save motor trim "
                    + "calibration."
                )
            );
        }

        renderCalibration(
            payload
        );

        showTemporaryMessage(
            motorsMessage,
            "Motor trim calibration saved.",
            () => (
                leftTrimValue === savedLeftTrim
                && rightTrimValue === savedRightTrim
            ),
        );

        announcement.textContent = (
            "Motor trim calibration saved."
        );
    } catch (error) {
        renderMotorEditor();

        motorsMessage.textContent = (
            error instanceof Error
                ? error.message
                : (
                    "Unable to save motor trim "
                    + "calibration."
                )
        );
    } finally {
        refreshButton.disabled = false;
    }
}


function setMotorControlsDisabled(
    disabled,
) {
    leftTrimIncreaseButton.disabled = disabled;
    leftTrimDecreaseButton.disabled = disabled;
    rightTrimIncreaseButton.disabled = disabled;
    rightTrimDecreaseButton.disabled = disabled;
    motorsPreviewButton.disabled = disabled;

    if (disabled) {
        motorsSaveButton.disabled = true;
        motorsResetButton.disabled = true;
    }
}


/* Camera */

function renderCameraMount(
    cameraMount,
) {
    const panOffset = Number(
        cameraMount.pan_offset
    );

    const tiltOffset = Number(
        cameraMount.tilt_offset
    );

    const validPanOffset = Number.isFinite(
        panOffset
    )
        ? panOffset
        : 0;

    const validTiltOffset = Number.isFinite(
        tiltOffset
    )
        ? tiltOffset
        : 0;

    savedCameraPanOffset = validPanOffset;
    savedCameraTiltOffset = validTiltOffset;

    cameraPanOffsetValue = validPanOffset;
    cameraTiltOffsetValue = validTiltOffset;

    renderCameraMountEditor();

    const adjusted = (
        validPanOffset !== 0
        || validTiltOffset !== 0
    );

    setBadge(
        cameraStatus,
        adjusted
            ? "Adjusted"
            : "Default",
        adjusted
            ? "healthy"
            : "neutral",
    );
}


function renderCameraMountEditor() {
    cameraPanOffset.textContent = formatOffset(
        cameraPanOffsetValue
    );

    cameraTiltOffset.textContent = formatOffset(
        cameraTiltOffsetValue
    );

    const changed = (
        cameraPanOffsetValue
            !== savedCameraPanOffset
        || cameraTiltOffsetValue
            !== savedCameraTiltOffset
    );

    cameraSaveButton.disabled = !changed;
    cameraResetButton.disabled = !changed;

    cameraMessage.textContent = (
        changed
            ? "Unsaved camera mount changes."
            : ""
    );
}


async function previewCameraMount() {
    const response = await fetch(
        "/api/calibration/camera-mount/preview",
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json",
                Accept:
                    "application/json",
            },

            body: JSON.stringify({
                pan_offset:
                    cameraPanOffsetValue,

                tilt_offset:
                    cameraTiltOffsetValue,
            }),
        },
    );

    let payload;

    try {
        payload = await response.json();
    } catch {
        throw new Error(
            "Camera mount API returned an "
            + "invalid response."
        );
    }

    if (!response.ok) {
        throw new Error(
            payload.message
            ?? "Unable to move camera."
        );
    }
}


function scheduleCameraPreview() {
    if (cameraPreviewTimer !== null) {
        window.clearTimeout(
            cameraPreviewTimer
        );
    }

    cameraPreviewTimer = window.setTimeout(
        async () => {
            cameraPreviewTimer = null;

            setCameraControlsDisabled(
                true
            );

            try {
                await previewCameraMount();
            } catch (error) {
                cameraMessage.textContent = (
                    error instanceof Error
                        ? error.message
                        : "Unable to move camera."
                );
            } finally {
                setCameraControlsDisabled(
                    false
                );

                renderCameraMountEditor();
            }
        },
        75,
    );
}


async function saveCameraMount() {
    cameraSaveButton.disabled = true;
    cameraResetButton.disabled = true;
    refreshButton.disabled = true;

    cameraMessage.textContent =
        "Saving…";

    try {
        const response = await fetch(
            "/api/calibration/camera-mount",
            {
                method: "PUT",

                headers: {
                    "Content-Type":
                        "application/json",
                    Accept:
                        "application/json",
                },

                body: JSON.stringify({
                    pan_offset:
                        cameraPanOffsetValue,

                    tilt_offset:
                        cameraTiltOffsetValue,
                }),
            },
        );

        let payload;

        try {
            payload = await response.json();
        } catch {
            throw new Error(
                "Calibration API returned an "
                + "invalid response."
            );
        }

        if (!response.ok) {
            throw new Error(
                payload.message
                ?? (
                    "Unable to save camera mount "
                    + "calibration."
                )
            );
        }

        renderCalibration(
            payload
        );

        showTemporaryMessage(
            cameraMessage,
            "Camera mount calibration saved.",
            () => (
                cameraPanOffsetValue
                    === savedCameraPanOffset
                && cameraTiltOffsetValue
                    === savedCameraTiltOffset
            ),
        );

        announcement.textContent = (
            "Camera mount calibration saved."
        );
    } catch (error) {
        renderCameraMountEditor();

        cameraMessage.textContent = (
            error instanceof Error
                ? error.message
                : (
                    "Unable to save camera mount "
                    + "calibration."
                )
        );
    } finally {
        refreshButton.disabled = false;
    }
}


function restoreSavedCameraMount() {
    if (cameraPreviewTimer !== null) {
        window.clearTimeout(
            cameraPreviewTimer
        );

        cameraPreviewTimer = null;
    }

    if (
        cameraPanOffsetValue
            === savedCameraPanOffset
        && cameraTiltOffsetValue
            === savedCameraTiltOffset
    ) {
        return;
    }

    fetch(
        "/api/calibration/camera-mount/preview",
        {
            method: "POST",
            keepalive: true,

            headers: {
                "Content-Type":
                    "application/json",
            },

            body: JSON.stringify({
                pan_offset:
                    savedCameraPanOffset,

                tilt_offset:
                    savedCameraTiltOffset,
            }),
        },
    ).catch(() => {});
}


function setCameraControlsDisabled(
    disabled,
) {
    cameraPanIncreaseButton.disabled =
        disabled;

    cameraPanDecreaseButton.disabled =
        disabled;

    cameraTiltIncreaseButton.disabled =
        disabled;

    cameraTiltDecreaseButton.disabled =
        disabled;

    if (disabled) {
        cameraSaveButton.disabled = true;
        cameraResetButton.disabled = true;
    }
}


/* Grayscale */

function renderSensorValues(
    element,
    values,
) {
    const validValues = copySensorValues(
        values
    );

    element.replaceChildren();

    const displayedValues = (
        validValues
        ?? [null, null, null]
    );

    for (const value of displayedValues) {
        const item = document.createElement(
            "span"
        );

        item.textContent = (
            value === null
                ? "—"
                : (
                    Number.isInteger(value)
                        ? String(value)
                        : value.toFixed(1)
                )
        );

        element.appendChild(
            item
        );
    }
}


function copySensorValues(
    values,
) {
    if (
        !Array.isArray(values)
        || values.length !== 3
    ) {
        return null;
    }

    const numbers = values.map(
        (value) => Number(value)
    );

    return numbers.every(
        Number.isFinite
    )
        ? numbers
        : null;
}


function sensorValuesEqual(
    first,
    second,
) {
    if (
        first === null
        || second === null
    ) {
        return first === second;
    }

    return first.every(
        (value, index) => (
            value === second[index]
        )
    );
}


function renderGrayscale(
    grayscale,
) {
    grayscaleCalibratedValue = Boolean(
        grayscale.calibrated
    );

    savedGrayscaleFloor = (
        grayscaleCalibratedValue
            ? copySensorValues(
                grayscale.floor
            )
            : null
    );

    savedGrayscaleLine = (
        grayscaleCalibratedValue
            ? copySensorValues(
                grayscale.line
            )
            : null
    );

    grayscaleFloorValue = (
        savedGrayscaleFloor === null
            ? null
            : [...savedGrayscaleFloor]
    );

    grayscaleLineValue = (
        savedGrayscaleLine === null
            ? null
            : [...savedGrayscaleLine]
    );

    renderGrayscaleEditor();

    setBadge(
        grayscaleStatus,
        grayscaleCalibratedValue
            ? "Calibrated"
            : "Not Calibrated",
        grayscaleCalibratedValue
            ? "healthy"
            : "warning",
    );
}

function renderGrayscaleEditor() {
    renderSensorValues(
        grayscaleFloor,
        grayscaleFloorValue
    );

    renderSensorValues(
        grayscaleLine,
        grayscaleLineValue
    );

    const complete = (
        grayscaleFloorValue !== null
        && grayscaleLineValue !== null
    );

    const changed = (
        !sensorValuesEqual(
            grayscaleFloorValue,
            savedGrayscaleFloor,
        )
        || !sensorValuesEqual(
            grayscaleLineValue,
            savedGrayscaleLine,
        )
    );

    grayscaleSaveButton.disabled = (
        !complete
        || !changed
    );

    grayscaleResetButton.disabled = !changed;

    grayscaleClearButton.disabled = (
        !grayscaleCalibratedValue
    );

    grayscaleMessage.textContent = (
        changed
            ? (
                complete
                    ? "Unsaved line sensor calibration."
                    : "Capture both surfaces before saving."
            )
            : ""
    );
}


async function sampleGrayscale() {
    const response = await fetch(
        "/api/calibration/grayscale/sample",
        {
            headers: {
                Accept: "application/json",
            },
            cache: "no-store",
        },
    );

    let payload;

    try {
        payload = await response.json();
    } catch {
        throw new Error(
            "Line sensor API returned an "
            + "invalid response."
        );
    }

    if (!response.ok) {
        throw new Error(
            payload.message
            || "Unable to read the line sensor."
        );
    }

    const values = copySensorValues(
        payload.values
    );

    if (values === null) {
        throw new Error(
            "Line sensor returned invalid readings."
        );
    }

    return values;
}

async function captureGrayscaleFloor() {
    setGrayscaleControlsDisabled(
        true
    );

    refreshButton.disabled = true;

    grayscaleMessage.textContent = (
        "Reading floor surface…"
    );

    try {
        grayscaleFloorValue =
            await sampleGrayscale();

        renderGrayscaleEditor();

        grayscaleMessage.textContent = (
            "Floor reference captured."
        );

        announcement.textContent = (
            "Floor reference captured."
        );
    } catch (error) {
        renderGrayscaleEditor();

        grayscaleMessage.textContent = (
            error instanceof Error
                ? error.message
                : "Unable to capture floor reference."
        );
    } finally {
        setGrayscaleControlsDisabled(
            false
        );

        refreshButton.disabled = false;
    }
}


async function captureGrayscaleLine() {
    setGrayscaleControlsDisabled(
        true
    );

    refreshButton.disabled = true;

    grayscaleMessage.textContent = (
        "Reading line surface…"
    );

    try {
        grayscaleLineValue =
            await sampleGrayscale();

        renderGrayscaleEditor();

        grayscaleMessage.textContent = (
            "Line reference captured."
        );

        announcement.textContent = (
            "Line reference captured."
        );
    } catch (error) {
        renderGrayscaleEditor();

        grayscaleMessage.textContent = (
            error instanceof Error
                ? error.message
                : "Unable to capture line reference."
        );
    } finally {
        setGrayscaleControlsDisabled(
            false
        );

        refreshButton.disabled = false;
    }
}


async function saveGrayscale() {
    if (
        grayscaleFloorValue === null
        || grayscaleLineValue === null
    ) {
        grayscaleMessage.textContent = (
            "Capture both surfaces before saving."
        );

        return;
    }

    grayscaleSaveButton.disabled = true;
    grayscaleResetButton.disabled = true;
    refreshButton.disabled = true;

    grayscaleMessage.textContent = (
        "Saving line sensor calibration…"
    );

    try {
        const response = await fetch(
            "/api/calibration/grayscale",
            {
                method: "PUT",

                headers: {
                    "Content-Type":
                        "application/json",
                    Accept:
                        "application/json",
                },

                body: JSON.stringify({
                    floor: grayscaleFloorValue,
                    line: grayscaleLineValue,
                }),
            },
        );

        let payload;

        try {
            payload = await response.json();
        } catch {
            throw new Error(
                "Calibration API returned an "
                + "invalid response."
            );
        }

        if (!response.ok) {
            throw new Error(
                payload.message
                || (
                    "Unable to save line "
                    + "sensor calibration."
                )
            );
        }

        renderCalibration(
            payload
        );

        showTemporaryMessage(
            grayscaleMessage,
            "Line sensor calibration saved.",
            () => (
                sensorValuesEqual(
                    grayscaleFloorValue,
                    savedGrayscaleFloor,
                )
                && sensorValuesEqual(
                    grayscaleLineValue,
                    savedGrayscaleLine,
                )
            ),
        );

        announcement.textContent = (
            "Line sensor calibration saved."
        );
    } catch (error) {
        renderGrayscaleEditor();

        grayscaleMessage.textContent = (
            error instanceof Error
                ? error.message
                : (
                    "Unable to save line "
                    + "sensor calibration."
                )
        );
    } finally {
        refreshButton.disabled = false;
    }
}


async function clearGrayscale() {
    grayscaleClearButton.disabled = true;
    refreshButton.disabled = true;

    grayscaleMessage.textContent = (
        "Clearing line sensor calibration…"
    );

    try {
        const response = await fetch(
            "/api/calibration/grayscale/clear",
            {
                method: "POST",

                headers: {
                    Accept:
                        "application/json",
                },
            },
        );

        let payload;

        try {
            payload = await response.json();
        } catch {
            throw new Error(
                "Calibration API returned an "
                + "invalid response."
            );
        }

        if (!response.ok) {
            throw new Error(
                payload.message
                || (
                    "Unable to clear line "
                    + "sensor calibration."
                )
            );
        }

        renderCalibration(
            payload
        );

        showTemporaryMessage(
            grayscaleMessage,
            "Line sensor calibration cleared.",
            () => (
                !grayscaleCalibratedValue
            ),
        );

        announcement.textContent = (
            "Line sensor calibration cleared."
        );
    } catch (error) {
        renderGrayscaleEditor();

        grayscaleMessage.textContent = (
            error instanceof Error
                ? error.message
                : (
                    "Unable to clear line "
                    + "sensor calibration."
                )
        );
    } finally {
        refreshButton.disabled = false;
    }
}


function setGrayscaleControlsDisabled(
    disabled,
) {
    grayscaleCaptureFloorButton.disabled =
        disabled;

    grayscaleCaptureLineButton.disabled =
        disabled;

    if (disabled) {
        grayscaleSaveButton.disabled = true;
        grayscaleResetButton.disabled = true;
        grayscaleClearButton.disabled = true;
    }
}


function renderMetadata(
    payload,
) {
    const saved = Boolean(
        payload.saved
    );

    setBadge(
        sourceBadge,
        saved
            ? "Saved Calibration"
            : "Factory Defaults",
        saved
            ? "healthy"
            : "neutral",
    );

    const now = new Date();

    updatedTime.textContent = (
        `Updated ${now.toLocaleTimeString([], {
            hour: "numeric",
            minute: "2-digit",
        })}`
    );
}


function renderCalibration(
    payload,
) {
    const calibration = payload.calibration;

    if (
        !calibration
        || typeof calibration !== "object"
    ) {
        throw new Error(
            "Calibration API returned invalid data."
        );
    }

    renderSteering(
        calibration.steering
        ?? {}
    );

    renderCameraMount(
        calibration.camera_mount
        ?? {}
    );

    renderMotors(
        calibration.motors
        ?? {}
    );

    renderGrayscale(
        calibration.grayscale
        ?? {}
    );

    renderMetadata(
        payload
    );

    loadingPanel.hidden = true;
    errorPanel.hidden = true;
    contentPanel.hidden = false;

    refreshButton.disabled = false;

    setConnectionState(
        "connected",
        "Loaded",
    );

    announcement.textContent = (
        "Calibration loaded."
    );

    setSteeringControlsDisabled(
        false
    );

    setCameraControlsDisabled(
        false
    );

    setMotorControlsDisabled(
        false
    );

    setGrayscaleControlsDisabled(
        false
    );

    renderGrayscaleEditor();

    renderMotorEditor();

    renderCameraMountEditor();

    renderSteeringEditor();
}


async function loadCalibration() {
    showLoading();

    try {
        const response = await fetch(
            "/api/calibration",
            {
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            },
        );

        let payload;

        try {
            payload = await response.json();
        } catch {
            throw new Error(
                "Calibration API returned an invalid response."
            );
        }

        if (!response.ok) {
            throw new Error(
                payload.message
                || "Unable to load calibration."
            );
        }

        renderCalibration(
            payload
        );
    } catch (error) {
        showError(
            error instanceof Error
                ? error.message
                : "Unable to load calibration."
        );
    }
}


refreshButton.addEventListener(
    "click",
    loadCalibration,
);

retryButton.addEventListener(
    "click",
    loadCalibration,
);

steeringIncreaseButton.addEventListener(
    "click",
    () => {
        steeringOffsetValue = clamp(
            steeringOffsetValue
                + STEERING_STEP,
            STEERING_MIN,
            STEERING_MAX,
        );

        renderSteeringEditor();
        scheduleSteeringPreview();
    },
);

steeringDecreaseButton.addEventListener(
    "click",
    () => {
        steeringOffsetValue = clamp(
            steeringOffsetValue
                - STEERING_STEP,
            STEERING_MIN,
            STEERING_MAX,
        );

        renderSteeringEditor();
        scheduleSteeringPreview();
    },
);

steeringResetButton.addEventListener(
    "click",
    () => {
        steeringOffsetValue =
            savedSteeringOffset;

        renderSteeringEditor();
        scheduleSteeringPreview();

    },
);

steeringSaveButton.addEventListener(
    "click",
    saveSteering,
);

cameraPanIncreaseButton.addEventListener(
    "click",
    () => {
        cameraPanOffsetValue = clamp(
            cameraPanOffsetValue
                + CAMERA_OFFSET_STEP,
            CAMERA_OFFSET_MIN,
            CAMERA_OFFSET_MAX,
        );

        renderCameraMountEditor();
        scheduleCameraPreview();
    },
);

cameraPanDecreaseButton.addEventListener(
    "click",
    () => {
        cameraPanOffsetValue = clamp(
            cameraPanOffsetValue
                - CAMERA_OFFSET_STEP,
            CAMERA_OFFSET_MIN,
            CAMERA_OFFSET_MAX,
        );

        renderCameraMountEditor();
        scheduleCameraPreview();
    },
);

cameraTiltIncreaseButton.addEventListener(
    "click",
    () => {
        cameraTiltOffsetValue = clamp(
            cameraTiltOffsetValue
                + CAMERA_OFFSET_STEP,
            CAMERA_OFFSET_MIN,
            CAMERA_OFFSET_MAX,
        );

        renderCameraMountEditor();
        scheduleCameraPreview();
    },
);

cameraTiltDecreaseButton.addEventListener(
    "click",
    () => {
        cameraTiltOffsetValue = clamp(
            cameraTiltOffsetValue
                - CAMERA_OFFSET_STEP,
            CAMERA_OFFSET_MIN,
            CAMERA_OFFSET_MAX,
        );

        renderCameraMountEditor();
        scheduleCameraPreview();
    },
);

cameraResetButton.addEventListener(
    "click",
    () => {
        cameraPanOffsetValue =
            savedCameraPanOffset;

        cameraTiltOffsetValue =
            savedCameraTiltOffset;

        renderCameraMountEditor();
        scheduleCameraPreview();

    },
);

cameraSaveButton.addEventListener(
    "click",
    saveCameraMount,
);

leftTrimIncreaseButton.addEventListener(
    "click",
    () => {
        leftTrimValue = clamp(
            Number(
                (
                    leftTrimValue
                    + MOTOR_TRIM_STEP
                ).toFixed(2)
            ),
            MOTOR_TRIM_MIN,
            MOTOR_TRIM_MAX,
        );

        renderMotorEditor();
    },
);

leftTrimDecreaseButton.addEventListener(
    "click",
    () => {
        leftTrimValue = clamp(
            Number(
                (
                    leftTrimValue
                    - MOTOR_TRIM_STEP
                ).toFixed(2)
            ),
            MOTOR_TRIM_MIN,
            MOTOR_TRIM_MAX,
        );

        renderMotorEditor();
    },
);

rightTrimIncreaseButton.addEventListener(
    "click",
    () => {
        rightTrimValue = clamp(
            Number(
                (
                    rightTrimValue
                    + MOTOR_TRIM_STEP
                ).toFixed(2)
            ),
            MOTOR_TRIM_MIN,
            MOTOR_TRIM_MAX,
        );

        renderMotorEditor();
    },
);

rightTrimDecreaseButton.addEventListener(
    "click",
    () => {
        rightTrimValue = clamp(
            Number(
                (
                    rightTrimValue
                    - MOTOR_TRIM_STEP
                ).toFixed(2)
            ),
            MOTOR_TRIM_MIN,
            MOTOR_TRIM_MAX,
        );

        renderMotorEditor();
    },
);

motorsResetButton.addEventListener(
    "click",
    () => {
        leftTrimValue = savedLeftTrim;
        rightTrimValue = savedRightTrim;

        renderMotorEditor();

        motorsMessage.textContent = (
            "Motor trim changes discarded."
        );
    },
);

motorsPreviewButton.addEventListener(
    "click",
    runMotorPreview,
);

motorsSaveButton.addEventListener(
    "click",
    saveMotors,
);

grayscaleResetButton.addEventListener(
    "click",
    () => {
        grayscaleFloorValue = (
            savedGrayscaleFloor === null
                ? null
                : [...savedGrayscaleFloor]
        );

        grayscaleLineValue = (
            savedGrayscaleLine === null
                ? null
                : [...savedGrayscaleLine]
        );

        renderGrayscaleEditor();

        grayscaleMessage.textContent = (
            "Line sensor changes discarded."
        );
    },
);

grayscaleCaptureFloorButton.addEventListener(
    "click",
    captureGrayscaleFloor,
);

grayscaleCaptureLineButton.addEventListener(
    "click",
    captureGrayscaleLine,
);

grayscaleSaveButton.addEventListener(
    "click",
    saveGrayscale,
);

grayscaleClearButton.addEventListener(
    "click",
    clearGrayscale,
);

window.addEventListener(
    "pagehide",
    () => {
        restorePreviewState();
    },
);

loadCalibration();
