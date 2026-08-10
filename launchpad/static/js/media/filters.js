"use strict";

import { CATEGORY_LABELS } from "./constants.js";

import { elements } from "./dom.js";

import { dateTimestamp } from "./helpers.js";

import { state } from "./state.js";

function sortFiles(files) {
    const sorted = [...files];

    sorted.sort((left, right) => {
        switch (state.sort) {
            case "oldest":
                return (
                    dateTimestamp(left.modifiedAt) -
                    dateTimestamp(right.modifiedAt)
                );

            case "name-ascending":
                return left.name.localeCompare(right.name, undefined, {
                    numeric: true,
                    sensitivity: "base",
                });

            case "name-descending":
                return right.name.localeCompare(left.name, undefined, {
                    numeric: true,
                    sensitivity: "base",
                });

            case "size-descending":
                return right.sizeBytes - left.sizeBytes;

            case "size-ascending":
                return left.sizeBytes - right.sizeBytes;

            case "newest":
            default:
                return (
                    dateTimestamp(right.modifiedAt) -
                    dateTimestamp(left.modifiedAt)
                );
        }
    });

    return sorted;
}

export function filteredFiles() {
    const query = state.search.trim().toLocaleLowerCase();

    const filtered = state.media.filter((file) => {
        const categoryMatches =
            state.category === "all" || file.category === state.category;

        const searchMatches =
            query.length === 0 || file.name.toLocaleLowerCase().includes(query);

        return categoryMatches && searchMatches;
    });

    return sortFiles(filtered);
}

export function updateFilterButtons() {
    for (const button of elements.categoryFilters) {
        const category = button.dataset.mediaCategory;

        const active = category === state.category;

        button.classList.toggle("is-active", active);

        button.setAttribute("aria-pressed", String(active));
    }
}

export function updateViewButtons() {
    const gridActive = state.view === "grid";

    elements.gridViewButton.classList.toggle("is-active", gridActive);

    elements.gridViewButton.setAttribute("aria-pressed", String(gridActive));

    elements.listViewButton.classList.toggle("is-active", !gridActive);

    elements.listViewButton.setAttribute("aria-pressed", String(!gridActive));

    elements.items.classList.toggle("media-grid", gridActive);

    elements.items.classList.toggle("media-list", !gridActive);
}

export function setCategory(category) {
    if (category !== "all" && !Object.hasOwn(CATEGORY_LABELS, category)) {
        return false;
    }

    state.category = category;

    updateFilterButtons();

    return true;
}

export function setSearch(value) {
    state.search = String(value);
}

export function setSort(value) {
    const allowedSorts = new Set([
        "newest",
        "oldest",
        "name-ascending",
        "name-descending",
        "size-descending",
        "size-ascending",
    ]);

    if (!allowedSorts.has(value)) {
        return false;
    }

    state.sort = value;

    return true;
}

export function setView(view) {
    if (view !== "grid" && view !== "list") {
        return false;
    }

    state.view = view;

    updateViewButtons();

    return true;
}
