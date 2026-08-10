"use strict";

import { elements } from "./dom.js";

import { displayValue } from "./helpers.js";

export function renderSoftware(software) {
    elements.softwareVersion.textContent = displayValue(
        software.betabox_robotics_version,
    );

    elements.pythonVersion.textContent = displayValue(software.python_version);

    elements.operatingSystem.textContent = displayValue(
        software.operating_system,
    );

    elements.architecture.textContent = displayValue(software.architecture);
}
