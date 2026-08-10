"use strict";

import { elements } from "./dom.js";

export function renderComponentOptions(components) {
    const selectedValue = elements.componentFilter.value;

    const defaultOption = document.createElement("option");

    defaultOption.value = "";

    defaultOption.textContent = "All components";

    elements.componentFilter.replaceChildren(defaultOption);

    if (!Array.isArray(components)) {
        return;
    }

    for (const component of components) {
        if (typeof component !== "string") {
            continue;
        }

        const value = component.trim();

        if (value === "") {
            continue;
        }

        const option = document.createElement("option");

        option.value = value;

        option.textContent = value;

        elements.componentFilter.append(option);
    }

    const availableValues = Array.from(elements.componentFilter.options).map(
        (option) => option.value,
    );

    if (availableValues.includes(selectedValue)) {
        elements.componentFilter.value = selectedValue;
    }
}

export function clearFilters() {
    elements.severityFilter.value = "";

    elements.componentFilter.value = "";

    elements.limitFilter.value = "50";
}
