"use strict";

const PREFERENCES_API_URL = "/api/preferences";

const DEFAULT_PREFERENCES = Object.freeze({
    theme: "system",
    reduced_motion: false,
    larger_text: false,
    compact_layout: false,
});

/* DOM */

const root = document.documentElement;

const systemThemeQuery = window.matchMedia("(prefers-color-scheme: dark)");

/* Validation */

function isTheme(value) {
    return value === "light" || value === "dark" || value === "system";
}

function isBooleanPreference(value) {
    return (
        value === true ||
        value === false ||
        value === "true" ||
        value === "false"
    );
}

/* Theme helpers */

function systemTheme() {
    return systemThemeQuery.matches ? "dark" : "light";
}

function selectedTheme() {
    const theme = root.dataset.theme;

    if (isTheme(theme)) {
        return theme;
    }

    return "system";
}

function activeTheme() {
    const theme = selectedTheme();

    return theme === "system" ? systemTheme() : theme;
}

function dispatchThemeChanged() {
    document.dispatchEvent(
        new CustomEvent("betabox:theme-changed", {
            detail: {
                selectedTheme: selectedTheme(),
                activeTheme: activeTheme(),
            },
        }),
    );
}

function applyTheme(theme) {
    if (!isTheme(theme)) {
        throw new TypeError("theme must be light, dark, or system");
    }

    if (theme === "system") {
        delete root.dataset.theme;
    } else {
        root.dataset.theme = theme;
    }

    dispatchThemeChanged();
}

/* Preference helpers */

function normalizeBooleanPreference(value, name) {
    if (!isBooleanPreference(value)) {
        throw new TypeError(`${name} must be a boolean`);
    }

    return value === true || value === "true";
}

function applyBooleanPreference(datasetKey, value, name) {
    const enabled = normalizeBooleanPreference(value, name);

    root.dataset[datasetKey] = enabled ? "true" : "false";
}

function currentLaunchpadPreferences() {
    return {
        theme: selectedTheme(),

        reduced_motion: root.dataset.reducedMotion === "true",

        larger_text: root.dataset.largerText === "true",

        compact_layout: root.dataset.compactLayout === "true",
    };
}

function applyLaunchpadPreferences({
    theme,
    reducedMotion,
    largerText,
    compactLayout,
} = {}) {
    if (theme !== undefined) {
        applyTheme(theme);
    }

    if (reducedMotion !== undefined) {
        applyBooleanPreference("reducedMotion", reducedMotion, "reducedMotion");
    }

    if (largerText !== undefined) {
        applyBooleanPreference("largerText", largerText, "largerText");
    }

    if (compactLayout !== undefined) {
        applyBooleanPreference("compactLayout", compactLayout, "compactLayout");
    }

    document.dispatchEvent(
        new CustomEvent("betabox:preferences-changed", {
            detail: {
                theme: selectedTheme(),
                activeTheme: activeTheme(),
                reducedMotion: root.dataset.reducedMotion === "true",
                largerText: root.dataset.largerText === "true",
                compactLayout: root.dataset.compactLayout === "true",
            },
        }),
    );
}

function normalizePreferences(value) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
        return {
            ...DEFAULT_PREFERENCES,
        };
    }

    return {
        theme: isTheme(value.theme) ? value.theme : DEFAULT_PREFERENCES.theme,

        reduced_motion: value.reduced_motion === true,

        larger_text: value.larger_text === true,

        compact_layout: value.compact_layout === true,
    };
}

async function saveLaunchpadPreferences(preferences) {
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

    return normalizePreferences(await response.json());
}

async function requestLaunchpadPreferences() {
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

    return normalizePreferences(await response.json());
}

async function loadLaunchpadPreferences() {
    try {
        const preferences = await requestLaunchpadPreferences();

        applyLaunchpadPreferences({
            theme: preferences.theme,
            reducedMotion: preferences.reduced_motion,
            largerText: preferences.larger_text,
            compactLayout: preferences.compact_layout,
        });

        return preferences;
    } catch (error) {
        console.error("Unable to load Launchpad preferences:", error);

        return currentLaunchpadPreferences();
    }
}

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
        console.debug("Unable to parse Preferences API error response:", error);
    }

    return message;
}

/* Theme toggle */

function configureThemeToggle() {
    const toggle = document.getElementById("theme-toggle");

    if (!(toggle instanceof HTMLButtonElement)) {
        return;
    }

    const updateLabel = () => {
        const active = activeTheme();
        const next = active === "dark" ? "light" : "dark";

        toggle.textContent = active === "dark" ? "Light Mode" : "Dark Mode";

        const label = `Switch to ${next} mode`;

        toggle.setAttribute("aria-label", label);
        toggle.setAttribute("title", label);
    };

    toggle.addEventListener("click", async () => {
        if (toggle.disabled) {
            return;
        }

        const previousTheme = selectedTheme();

        const nextTheme = activeTheme() === "dark" ? "light" : "dark";

        toggle.disabled = true;

        applyTheme(nextTheme);

        try {
            const preferences = await saveLaunchpadPreferences(
                currentLaunchpadPreferences(),
            );

            applyLaunchpadPreferences({
                theme: preferences.theme,
                reducedMotion: preferences.reduced_motion,
                largerText: preferences.larger_text,
                compactLayout: preferences.compact_layout,
            });
        } catch (error) {
            console.error("Unable to save Launchpad theme:", error);

            applyTheme(previousTheme);
        } finally {
            toggle.disabled = false;
        }
    });

    document.addEventListener("betabox:theme-changed", updateLabel);

    updateLabel();
}

/* System preference changes */

systemThemeQuery.addEventListener("change", () => {
    if (selectedTheme() === "system") {
        dispatchThemeChanged();
    }
});

/* Public API */

window.applyTheme = applyTheme;
window.applyLaunchpadPreferences = applyLaunchpadPreferences;

window.betaboxPreferences = {
    activeTheme,
    applyLaunchpadPreferences,
    applyTheme,
    current: currentLaunchpadPreferences,
    loadLaunchpadPreferences,
    saveLaunchpadPreferences,
    selectedTheme,
    systemTheme,
};

/* Startup */

async function initializeTheme() {
    await loadLaunchpadPreferences();

    configureThemeToggle();
}

if (document.readyState === "loading") {
    document.addEventListener(
        "DOMContentLoaded",
        () => {
            void initializeTheme();
        },
        {
            once: true,
        },
    );
} else {
    void initializeTheme();
}
