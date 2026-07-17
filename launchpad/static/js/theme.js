"use strict";

const THEME_STORAGE_KEY =
    "betabox-launchpad-theme";

const REDUCED_MOTION_STORAGE_KEY =
    "betabox-launchpad-reduced-motion";

const LARGER_TEXT_STORAGE_KEY =
    "betabox-launchpad-larger-text";

const COMPACT_LAYOUT_STORAGE_KEY =
    "betabox-launchpad-compact-layout";

const root =
    document.documentElement;


function storedTheme() {
    const value =
        window.localStorage.getItem(
            THEME_STORAGE_KEY
        );

    if (
        value === "light"
        || value === "dark"
    ) {
        return value;
    }

    return null;
}

function useSystemTheme() {
    window.localStorage.removeItem(
        THEME_STORAGE_KEY
    );

    delete root.dataset.theme;

    document.dispatchEvent(
        new CustomEvent(
            "betabox:theme-changed",
            {
                detail: {
                    theme: systemTheme(),
                },
            }
        )
    );
}

function systemTheme() {
    return window.matchMedia(
        "(prefers-color-scheme: dark)"
    ).matches
        ? "dark"
        : "light";
}


function activeTheme() {
    return (
        root.dataset.theme
        || storedTheme()
        || systemTheme()
    );
}


function storedBooleanPreference(
    key
) {
    return (
        window.localStorage.getItem(key)
        === "true"
    );
}


function applyLaunchpadPreferences() {
    root.dataset.reducedMotion = (
        storedBooleanPreference(
            REDUCED_MOTION_STORAGE_KEY
        )
            ? "true"
            : "false"
    );

    root.dataset.largerText = (
        storedBooleanPreference(
            LARGER_TEXT_STORAGE_KEY
        )
            ? "true"
            : "false"
    );

    root.dataset.compactLayout = (
        storedBooleanPreference(
            COMPACT_LAYOUT_STORAGE_KEY
        )
            ? "true"
            : "false"
    );
}


function applyTheme(
    theme,
    {
        persist = false,
    } = {}
) {
    if (
        theme !== "light"
        && theme !== "dark"
    ) {
        return;
    }

    root.dataset.theme = theme;

    if (persist) {
        window.localStorage.setItem(
            THEME_STORAGE_KEY,
            theme
        );
    }

    document.dispatchEvent(
        new CustomEvent(
            "betabox:theme-changed",
            {
                detail: {
                    theme,
                },
            }
        )
    );
}


function toggleTheme() {
    applyTheme(
        activeTheme() === "dark"
            ? "light"
            : "dark",
        {
            persist: true,
        }
    );
}


function configureThemeToggle() {
    const toggle =
        document.getElementById(
            "theme-toggle"
        );

    if (toggle === null) {
        return;
    }

    const updateLabel = () => {
        const theme =
            activeTheme();

        toggle.textContent =
            theme === "dark"
                ? "Switch to Light Mode"
                : "Switch to Dark Mode";

        toggle.setAttribute(
            "aria-label",
            theme === "dark"
                ? "Switch to light mode"
                : "Switch to dark mode"
        );
    };

    toggle.addEventListener(
        "click",
        () => {
            toggleTheme();
            updateLabel();
        }
    );

    updateLabel();
}

window.applyTheme = applyTheme;
window.useSystemTheme = useSystemTheme;

window.applyLaunchpadPreferences = (
    applyLaunchpadPreferences
);

window.betaboxPreferences = {
    applyTheme,
    applyLaunchpadPreferences,
    activeTheme,
    systemTheme,
    useSystemTheme,
};


const initialTheme = storedTheme();

if (initialTheme !== null) {
    applyTheme(initialTheme);
} else {
    useSystemTheme();
}

applyLaunchpadPreferences();

const systemThemeQuery = window.matchMedia(
    "(prefers-color-scheme: dark)"
);

systemThemeQuery.addEventListener(
    "change",
    () => {
        if (
            storedTheme() === null
            && !root.dataset.theme
        ) {
            document.dispatchEvent(
                new CustomEvent(
                    "betabox:theme-changed",
                    {
                        detail: {
                            theme: systemTheme(),
                        },
                    }
                )
            );
        }
    }
);

document.addEventListener(
    "DOMContentLoaded",
    configureThemeToggle
);
