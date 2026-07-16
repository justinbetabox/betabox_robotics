"use strict";

const THEME_STORAGE_KEY =
    "betabox-launchpad-theme";

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


const initialTheme =
    storedTheme();

if (initialTheme !== null) {
    applyTheme(
        initialTheme
    );
}


document.addEventListener(
    "DOMContentLoaded",
    configureThemeToggle
);
