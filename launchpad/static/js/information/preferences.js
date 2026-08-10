"use strict";

import { PREFERENCES_API_URL } from "./constants.js";

import { elements } from "./dom.js";

const DEFAULT_PREFERENCES = Object.freeze({
    theme: "system",
    reduced_motion: false,
    larger_text: false,
    compact_layout: false,
});

let preferenceRequestVersion = 0;

let statusTimer = null;

/* Validation */

function isTheme(value) {
    return value === "system" || value === "light" || value === "dark";
}

function validatePreferences(payload) {
    if (
        payload === null ||
        typeof payload !== "object" ||
        Array.isArray(payload)
    ) {
        throw new Error("The preferences API returned an invalid response.");
    }

    if (!isTheme(payload.theme)) {
        throw new Error("The preferences response contains an invalid theme.");
    }

    for (const name of ["reduced_motion", "larger_text", "compact_layout"]) {
        if (typeof payload[name] !== "boolean") {
            throw new Error(
                `The preferences response contains an invalid ${name}.`,
            );
        }
    }

    return payload;
}

/* API */

async function responseErrorMessage(response) {
    let message = `Preferences API returned HTTP ${response.status}.`;

    try {
        const payload = await response.json();

        if (
            payload !== null &&
            typeof payload === "object" &&
            !Array.isArray(payload) &&
            typeof payload.message === "string" &&
            payload.message.trim() !== ""
        ) {
            message = payload.message.trim();
        }
    } catch (error) {
        console.debug("Unable to parse preferences API error response:", error);
    }

    return message;
}

async function requestPreferences() {
    const response = await fetch(PREFERENCES_API_URL, {
        method: "GET",
        headers: {
            Accept: "application/json",
        },
        cache: "no-store",
    });

    if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
    }

    return validatePreferences(await response.json());
}

async function savePreferences(preferences) {
    const response = await fetch(PREFERENCES_API_URL, {
        method: "PUT",
        headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
        },
        cache: "no-store",
        body: JSON.stringify(preferences),
    });

    if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
    }

    return validatePreferences(await response.json());
}

async function resetPreferences() {
    const response = await fetch(PREFERENCES_API_URL, {
        method: "DELETE",
        headers: {
            Accept: "application/json",
        },
        cache: "no-store",
    });

    if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
    }

    return validatePreferences(await response.json());
}

/* Form */

function appearanceInputs() {
    return Array.from(
        document.querySelectorAll('input[name="appearance"]'),
    ).filter((input) => input instanceof HTMLInputElement);
}

function selectedTheme() {
    const selected = appearanceInputs().find((input) => input.checked);

    return selected?.value ?? "system";
}

function setThemeSelection(theme) {
    for (const input of appearanceInputs()) {
        input.checked = input.value === theme;
    }
}

function preferencesFromForm() {
    return {
        theme: selectedTheme(),
        reduced_motion: elements.reducedMotion.checked,
        larger_text: elements.largerText.checked,
        compact_layout: elements.compactLayout.checked,
    };
}

function renderPreferences(preferences) {
    setThemeSelection(preferences.theme);

    elements.reducedMotion.checked = preferences.reduced_motion;

    elements.largerText.checked = preferences.larger_text;

    elements.compactLayout.checked = preferences.compact_layout;
}

/* Global application */

function applyPreferences(preferences) {
    if (typeof window.applyLaunchpadPreferences !== "function") {
        throw new Error("Launchpad preferences API is unavailable.");
    }

    window.applyLaunchpadPreferences({
        theme: preferences.theme,
        reducedMotion: preferences.reduced_motion,
        largerText: preferences.larger_text,
        compactLayout: preferences.compact_layout,
    });
}

/* Status */

function showPreferenceStatus(message) {
    elements.preferencesStatus.textContent = message;

    if (statusTimer !== null) {
        window.clearTimeout(statusTimer);
    }

    statusTimer = window.setTimeout(() => {
        elements.preferencesStatus.textContent = "";

        statusTimer = null;
    }, 1800);
}

/* Persistence */

async function persistFormPreferences() {
    const requestVersion = ++preferenceRequestVersion;

    const requestedPreferences = preferencesFromForm();

    try {
        const preferences = await savePreferences(requestedPreferences);

        if (requestVersion !== preferenceRequestVersion) {
            return;
        }

        renderPreferences(preferences);

        applyPreferences(preferences);

        showPreferenceStatus("Preferences saved");
    } catch (error) {
        if (requestVersion !== preferenceRequestVersion) {
            return;
        }

        console.error("Unable to save Launchpad preferences:", error);

        showPreferenceStatus("Unable to save preferences");
    }
}

async function restoreDefaultPreferences() {
    const requestVersion = ++preferenceRequestVersion;

    try {
        const preferences = await resetPreferences();

        if (requestVersion !== preferenceRequestVersion) {
            return;
        }

        renderPreferences(preferences);

        applyPreferences(preferences);

        showPreferenceStatus("Preferences reset");
    } catch (error) {
        if (requestVersion !== preferenceRequestVersion) {
            return;
        }

        console.error("Unable to reset Launchpad preferences:", error);

        showPreferenceStatus("Unable to reset preferences");
    }
}

/* Initialization */

export async function initializePreferences() {
    let preferences = DEFAULT_PREFERENCES;

    try {
        preferences = await requestPreferences();
    } catch (error) {
        console.error("Unable to load Launchpad preferences:", error);
    }

    renderPreferences(preferences);

    applyPreferences(preferences);

    for (const input of appearanceInputs()) {
        input.addEventListener("change", () => {
            void persistFormPreferences();
        });
    }

    elements.reducedMotion.addEventListener("change", () => {
        void persistFormPreferences();
    });

    elements.largerText.addEventListener("change", () => {
        void persistFormPreferences();
    });

    elements.compactLayout.addEventListener("change", () => {
        void persistFormPreferences();
    });

    elements.resetPreferences.addEventListener("click", () => {
        void restoreDefaultPreferences();
    });
}
