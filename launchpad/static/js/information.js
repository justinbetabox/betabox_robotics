"use strict";

const INFORMATION_API_URL = "/api/information";

const THEME_KEY = "betabox-launchpad-theme";
const APPEARANCE_KEY =
    "betabox-launchpad-appearance";

const REDUCED_MOTION_KEY =
    "betabox-launchpad-reduced-motion";

const LARGER_TEXT_KEY =
    "betabox-launchpad-larger-text";

const COMPACT_LAYOUT_KEY =
    "betabox-launchpad-compact-layout";


const elements = {
    connection: document.getElementById(
        "information-connection"
    ),

    refreshButton: document.getElementById(
        "refresh-information"
    ),

    retryButton: document.getElementById(
        "retry-information"
    ),

    updated: document.getElementById(
        "information-updated"
    ),

    errorPanel: document.getElementById(
        "information-error-panel"
    ),

    errorMessage: document.getElementById(
        "information-error-message"
    ),

    robotModel: document.getElementById(
        "robot-model"
    ),

    robotHostname: document.getElementById(
        "robot-hostname"
    ),

    robotIdentifier: document.getElementById(
        "robot-identifier"
    ),

    robotControl: document.getElementById(
        "robot-control"
    ),

    robotControlBadge: document.getElementById(
        "robot-control-badge"
    ),

    networkHostname: document.getElementById(
        "network-hostname"
    ),

    ipAddresses: document.getElementById(
        "ip-addresses"
    ),

    launchpadUrls: document.getElementById(
        "launchpad-urls"
    ),

    jupyterhubUrls: document.getElementById(
        "jupyterhub-urls"
    ),

    visionUrls: document.getElementById(
        "vision-urls"
    ),

    softwareVersion: document.getElementById(
        "software-version"
    ),

    pythonVersion: document.getElementById(
        "python-version"
    ),

    operatingSystem: document.getElementById(
        "operating-system"
    ),

    architecture: document.getElementById(
        "architecture"
    ),

    storagePercent: document.getElementById(
        "storage-percent"
    ),

    storageMeterFill: document.getElementById(
        "storage-meter-fill"
    ),

    storageUsed: document.getElementById(
        "storage-used"
    ),

    storageAvailable: document.getElementById(
        "storage-available"
    ),

    storageTotal: document.getElementById(
        "storage-total"
    ),

    featureRobotControl: document.getElementById(
        "feature-robot-control"
    ),

    featureVisionService: document.getElementById(
        "feature-vision-service"
    ),

    featureCamera: document.getElementById(
        "feature-camera"
    ),

    featureJupyterhub: document.getElementById(
        "feature-jupyterhub"
    ),

    mediaPictures: document.getElementById(
        "media-pictures"
    ),

    mediaVideos: document.getElementById(
        "media-videos"
    ),

    mediaSounds: document.getElementById(
        "media-sounds"
    ),

    reducedMotion: document.getElementById(
        "reduced-motion"
    ),

    largerText: document.getElementById(
        "larger-text"
    ),

    compactLayout: document.getElementById(
        "compact-layout"
    ),

    resetPreferences: document.getElementById(
        "reset-preferences"
    ),

    preferencesStatus: document.getElementById(
        "preferences-status"
    ),
};


function setConnectionState(
    state,
    label
) {
    elements.connection.classList.remove(
        "status-connecting",
        "status-connected",
        "status-error"
    );

    if (state === "connected") {
        elements.connection.classList.add(
            "status-connected"
        );
    } else if (state === "error") {
        elements.connection.classList.add(
            "status-error"
        );
    } else {
        elements.connection.classList.add(
            "status-connecting"
        );
    }

    elements.connection.textContent = label;
}


function setLoadingState(
    loading
) {
    elements.refreshButton.disabled = loading;
    elements.retryButton.disabled = loading;

    elements.refreshButton.textContent = (
        loading
            ? "Refreshing…"
            : "Refresh"
    );

    if (loading) {
        setConnectionState(
            "connecting",
            "Loading…"
        );
    }
}


function showError(
    message
) {
    elements.errorMessage.textContent = message;
    elements.errorPanel.hidden = false;

    setConnectionState(
        "error",
        "Unavailable"
    );
}


function hideError() {
    elements.errorPanel.hidden = true;
}


function formatUpdatedTime(
    date
) {
    return new Intl.DateTimeFormat(
        undefined,
        {
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit",
        }
    ).format(date);
}


function displayValue(
    value,
    fallback = "Not available"
) {
    if (
        value === null
        || value === undefined
        || value === ""
    ) {
        return fallback;
    }

    return String(value);
}


function formatBytes(
    value
) {
    const bytes = Number(value);

    if (
        !Number.isFinite(bytes)
        || bytes < 0
    ) {
        return "Not available";
    }

    if (bytes === 0) {
        return "0 B";
    }

    const units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ];

    const unitIndex = Math.min(
        Math.floor(
            Math.log(bytes)
            / Math.log(1024)
        ),
        units.length - 1
    );

    const amount = (
        bytes
        / Math.pow(
            1024,
            unitIndex
        )
    );

    return `${amount.toFixed(
        amount >= 10 || unitIndex === 0
            ? 0
            : 1
    )} ${units[unitIndex]}`;
}


function clearBadgeClasses(
    badge
) {
    badge.classList.remove(
        "information-badge-healthy",
        "information-badge-warning",
        "information-badge-error",
        "information-badge-neutral"
    );
}


function setAvailabilityBadge(
    badge,
    available,
    {
        availableLabel = "Available",
        unavailableLabel = "Unavailable",
    } = {}
) {
    clearBadgeClasses(badge);

    if (available === true) {
        badge.classList.add(
            "information-badge-healthy"
        );

        badge.textContent = availableLabel;
    } else if (available === false) {
        badge.classList.add(
            "information-badge-warning"
        );

        badge.textContent = unavailableLabel;
    } else {
        badge.classList.add(
            "information-badge-neutral"
        );

        badge.textContent = "Unknown";
    }
}


function createValueItem(
    value
) {
    const item = document.createElement(
        "span"
    );

    item.className = "value-chip";
    item.textContent = value;

    return item;
}


function renderValueList(
    container,
    values
) {
    container.replaceChildren();

    if (
        !Array.isArray(values)
        || values.length === 0
    ) {
        container.textContent = "Not available";
        return;
    }

    for (const value of values) {
        container.append(
            createValueItem(value)
        );
    }
}


async function copyText(
    value,
    button
) {
    const originalLabel = (
        button.textContent
    );

    try {
        if (
            navigator.clipboard
            && window.isSecureContext
        ) {
            await navigator.clipboard.writeText(
                value
            );
        } else {
            const textarea = document.createElement(
                "textarea"
            );

            textarea.value = value;
            textarea.setAttribute(
                "readonly",
                ""
            );

            textarea.style.position = "fixed";
            textarea.style.opacity = "0";
            textarea.style.pointerEvents = "none";

            document.body.append(textarea);

            textarea.select();
            textarea.setSelectionRange(
                0,
                textarea.value.length
            );

            const copied = document.execCommand(
                "copy"
            );

            textarea.remove();

            if (!copied) {
                throw new Error(
                    "Browser copy command failed."
                );
            }
        }

        button.textContent = "Copied";

        window.setTimeout(
            () => {
                button.textContent = (
                    originalLabel
                );
            },
            1500
        );
    } catch (error) {
        console.error(
            "Unable to copy URL:",
            error
        );

        button.textContent = "Select";

        const link = button
            .closest(".url-item")
            ?.querySelector("a");

        if (link !== null) {
            const selection = (
                window.getSelection()
            );

            const range = (
                document.createRange()
            );

            range.selectNodeContents(link);

            selection?.removeAllRanges();
            selection?.addRange(range);
        }

        window.setTimeout(
            () => {
                button.textContent = (
                    originalLabel
                );
            },
            1800
        );
    }
}


function createUrlItem(
    value
) {
    const item = document.createElement(
        "div"
    );

    item.className = "url-item";

    const link = document.createElement(
        "a"
    );

    link.href = value;
    link.textContent = value;
    link.target = "_blank";
    link.rel = "noopener noreferrer";

    const copyButton = document.createElement(
        "button"
    );

    copyButton.className = (
        "url-copy-button"
    );

    copyButton.type = "button";
    copyButton.textContent = "Copy";

    copyButton.addEventListener(
        "click",
        () => {
            copyText(
                value,
                copyButton
            );
        }
    );

    item.append(
        link,
        copyButton
    );

    return item;
}


function renderUrlList(
    container,
    values
) {
    container.replaceChildren();

    if (
        !Array.isArray(values)
        || values.length === 0
    ) {
        container.textContent = "Not available";
        return;
    }

    for (const value of values) {
        container.append(
            createUrlItem(value)
        );
    }
}


function renderRobot(
    robot
) {
    elements.robotModel.textContent = (
        displayValue(robot.model)
    );

    elements.robotHostname.textContent = (
        displayValue(robot.hostname)
    );

    elements.robotIdentifier.textContent = (
        displayValue(robot.identifier)
    );

    const available = (
        robot.control_available
    );

    elements.robotControl.textContent = (
        available
            ? "Available for student code"
            : "Currently in use"
    );

    setAvailabilityBadge(
        elements.robotControlBadge,
        available,
        {
            availableLabel: "Available",
            unavailableLabel: "In Use",
        }
    );

    setAvailabilityBadge(
        elements.featureRobotControl,
        available,
        {
            availableLabel: "Available",
            unavailableLabel: "In Use",
        }
    );
}


function renderNetwork(
    network
) {
    elements.networkHostname.textContent = (
        displayValue(network.hostname)
    );

    renderValueList(
        elements.ipAddresses,
        network.ip_addresses
    );

    renderUrlList(
        elements.launchpadUrls,
        network.launchpad_urls
    );

    renderUrlList(
        elements.jupyterhubUrls,
        network.jupyterhub_urls
    );

    renderUrlList(
        elements.visionUrls,
        network.vision_urls
    );
}


function renderSoftware(
    software
) {
    elements.softwareVersion.textContent = (
        displayValue(
            software.betabox_robotics_version
        )
    );

    elements.pythonVersion.textContent = (
        displayValue(
            software.python_version
        )
    );

    elements.operatingSystem.textContent = (
        displayValue(
            software.operating_system
        )
    );

    elements.architecture.textContent = (
        displayValue(
            software.architecture
        )
    );
}


function renderStorage(
    storage
) {
    const rawUsedPercent = Number(
        storage.used_percent
    );

    const hasUsedPercent = (
        Number.isFinite(rawUsedPercent)
    );

    const usedPercent = (
        hasUsedPercent
            ? Math.min(
                100,
                Math.max(
                    0,
                    rawUsedPercent
                )
            )
            : 0
    );

    clearBadgeClasses(
        elements.storagePercent
    );

    if (!hasUsedPercent) {
        elements.storagePercent.textContent = (
            "Unknown"
        );

        elements.storagePercent.classList.add(
            "information-badge-neutral"
        );
    } else {
        elements.storagePercent.textContent = (
            `${usedPercent.toFixed(1)}% used`
        );

        if (usedPercent >= 95) {
            elements.storagePercent.classList.add(
                "information-badge-error"
            );
        } else if (usedPercent >= 85) {
            elements.storagePercent.classList.add(
                "information-badge-warning"
            );
        } else {
            elements.storagePercent.classList.add(
                "information-badge-healthy"
            );
        }
    }

    elements.storageMeterFill.style.width = (
        `${usedPercent}%`
    );

    const track = (
        elements.storageMeterFill
        .parentElement
    );

    if (track !== null) {
        track.setAttribute(
            "aria-valuenow",
            String(
                Math.round(usedPercent)
            )
        );
    }

    elements.storageUsed.textContent = (
        formatBytes(storage.used_bytes)
    );

    elements.storageAvailable.textContent = (
        formatBytes(
            storage.available_bytes
        )
    );

    elements.storageTotal.textContent = (
        formatBytes(storage.total_bytes)
    );
}


function renderFeatures(
    features
) {
    setAvailabilityBadge(
        elements.featureVisionService,
        features.vision_service_available,
        {
            availableLabel: "Running",
            unavailableLabel: "Unavailable",
        }
    );

    setAvailabilityBadge(
        elements.featureCamera,
        features.camera_ready,
        {
            availableLabel: "Ready",
            unavailableLabel: "Not Ready",
        }
    );

    setAvailabilityBadge(
        elements.featureJupyterhub,
        features.jupyterhub_available,
        {
            availableLabel: "Installed",
            unavailableLabel: "Unavailable",
        }
    );
}


function renderMedia(
    media
) {
    setAvailabilityBadge(
        elements.mediaPictures,
        media.pictures_available,
        {
            availableLabel: "Ready",
            unavailableLabel: "Missing",
        }
    );

    setAvailabilityBadge(
        elements.mediaVideos,
        media.videos_available,
        {
            availableLabel: "Ready",
            unavailableLabel: "Missing",
        }
    );

    setAvailabilityBadge(
        elements.mediaSounds,
        media.sounds_available,
        {
            availableLabel: "Ready",
            unavailableLabel: "Missing",
        }
    );
}


function validatePayload(
    payload
) {
    const sections = [
        "robot",
        "network",
        "software",
        "storage",
        "media",
        "features",
    ];

    if (
        !payload
        || typeof payload !== "object"
    ) {
        throw new Error(
            "The Information API returned an invalid response."
        );
    }

    for (const section of sections) {
        if (
            !payload[section]
            || typeof payload[section]
            !== "object"
        ) {
            throw new Error(
                `The information response is missing ${section}.`
            );
        }
    }
}


async function loadInformation() {
    setLoadingState(true);
    hideError();

    elements.updated.textContent = (
        "Loading platform information…"
    );

    try {
        const response = await fetch(
            INFORMATION_API_URL,
            {
                method: "GET",
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            }
        );

        if (!response.ok) {
            let message = (
                `Information API returned HTTP `
                + `${response.status}.`
            );

            try {
                const errorPayload = (
                    await response.json()
                );

                if (errorPayload.message) {
                    message = errorPayload.message;
                }
            } catch {
                // Preserve the HTTP error message.
            }

            throw new Error(message);
        }

        const payload = await response.json();

        validatePayload(payload);

        renderRobot(payload.robot);
        renderNetwork(payload.network);
        renderSoftware(payload.software);
        renderStorage(payload.storage);
        renderMedia(payload.media);
        renderFeatures(payload.features);

        elements.updated.textContent = (
            `Updated ${
                formatUpdatedTime(new Date())
            }`
        );

        setConnectionState(
            "connected",
            "Connected"
        );
    } catch (error) {
        console.error(
            "Unable to load platform information:",
            error
        );

        const message = (
            error instanceof Error
                ? error.message
                : "The Information API did not respond."
        );

        showError(message);

        elements.updated.textContent = (
            "Information unavailable"
        );
    } finally {
        setLoadingState(false);
    }
}


function preferenceBoolean(
    key
) {
    return (
        window.localStorage.getItem(key)
        === "true"
    );
}


function saveBooleanPreference(
    key,
    value
) {
    window.localStorage.setItem(
        key,
        value ? "true" : "false"
    );
}


function applyAppearance(
    appearance
) {
    if (appearance === "system") {
        window.localStorage.removeItem(
            THEME_KEY
        );

        if (
            typeof window.useSystemTheme
            === "function"
        ) {
            window.useSystemTheme();
        } else {
            delete document.documentElement
                .dataset.theme;
        }

        return;
    }

    if (
        appearance !== "light"
        && appearance !== "dark"
    ) {
        return;
    }

    if (
        typeof window.applyTheme
        === "function"
    ) {
        window.applyTheme(
            appearance,
            {
                persist: true,
            }
        );
    } else {
        document.documentElement.dataset.theme = (
            appearance
        );

        window.localStorage.setItem(
            THEME_KEY,
            appearance
        );
    }
}


function showPreferenceStatus(
    message
) {
    elements.preferencesStatus.textContent = (
        message
    );

    window.clearTimeout(
        showPreferenceStatus.timeoutId
    );

    showPreferenceStatus.timeoutId = (
        window.setTimeout(
            () => {
                elements.preferencesStatus
                    .textContent = "";
            },
            1800
        )
    );
}


showPreferenceStatus.timeoutId = 0;


function selectedAppearance() {
    const selected = document.querySelector(
        'input[name="appearance"]:checked'
    );

    return selected?.value || "system";
}


function setAppearanceSelection(
    appearance
) {
    const input = document.querySelector(
        `input[name="appearance"][value="${appearance}"]`
    );

    if (input !== null) {
        input.checked = true;
    }
}


function loadPreferences() {
    const savedAppearance = (
        window.localStorage.getItem(
            APPEARANCE_KEY
        )
        || (
            window.localStorage.getItem(
                THEME_KEY
            )
            || "system"
        )
    );

    setAppearanceSelection(
        savedAppearance
    );

    elements.reducedMotion.checked = (
        preferenceBoolean(
            REDUCED_MOTION_KEY
        )
    );

    elements.largerText.checked = (
        preferenceBoolean(
            LARGER_TEXT_KEY
        )
    );

    elements.compactLayout.checked = (
        preferenceBoolean(
            COMPACT_LAYOUT_KEY
        )
    );

    applyAppearance(
        savedAppearance
    );

    if (
        typeof window.applyLaunchpadPreferences
        === "function"
    ) {
        window.applyLaunchpadPreferences();
    }
}


function saveAppearancePreference() {
    const appearance = selectedAppearance();

    window.localStorage.setItem(
        APPEARANCE_KEY,
        appearance
    );

    applyAppearance(appearance);

    showPreferenceStatus(
        "Appearance saved"
    );
}


function saveDisplayPreferences() {
    saveBooleanPreference(
        REDUCED_MOTION_KEY,
        elements.reducedMotion.checked
    );

    saveBooleanPreference(
        LARGER_TEXT_KEY,
        elements.largerText.checked
    );

    saveBooleanPreference(
        COMPACT_LAYOUT_KEY,
        elements.compactLayout.checked
    );

    if (
        typeof window.applyLaunchpadPreferences
        === "function"
    ) {
        window.applyLaunchpadPreferences();
    }

    showPreferenceStatus(
        "Preferences saved"
    );
}


function resetPreferences() {
    for (const key of [
        APPEARANCE_KEY,
        THEME_KEY,
        REDUCED_MOTION_KEY,
        LARGER_TEXT_KEY,
        COMPACT_LAYOUT_KEY,
    ]) {
        window.localStorage.removeItem(key);
    }

    setAppearanceSelection("system");

    elements.reducedMotion.checked = false;
    elements.largerText.checked = false;
    elements.compactLayout.checked = false;

    applyAppearance("system");
    if (
        typeof window.applyLaunchpadPreferences
        === "function"
    ) {
        window.applyLaunchpadPreferences();
    }

    showPreferenceStatus(
        "Preferences reset"
    );
}


function setupEventListeners() {
    elements.refreshButton.addEventListener(
        "click",
        loadInformation
    );

    elements.retryButton.addEventListener(
        "click",
        loadInformation
    );

    document.querySelectorAll(
        'input[name="appearance"]'
    ).forEach(
        input => {
            input.addEventListener(
                "change",
                saveAppearancePreference
            );
        }
    );

    elements.reducedMotion.addEventListener(
        "change",
        saveDisplayPreferences
    );

    elements.largerText.addEventListener(
        "change",
        saveDisplayPreferences
    );

    elements.compactLayout.addEventListener(
        "change",
        saveDisplayPreferences
    );

    elements.resetPreferences.addEventListener(
        "click",
        resetPreferences
    );
}


function initializeInformationPage() {
    loadPreferences();
    setupEventListeners();
    loadInformation();
}


if (
    document.readyState === "loading"
) {
    document.addEventListener(
        "DOMContentLoaded",
        initializeInformationPage
    );
} else {
    initializeInformationPage();
}
