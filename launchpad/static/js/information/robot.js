"use strict";

import { elements } from "./dom.js";

import { displayValue, setAvailabilityBadge } from "./helpers.js";

export function renderRobot(robot) {
    elements.robotModel.textContent = displayValue(robot.model);

    elements.robotHostname.textContent = displayValue(robot.hostname);

    elements.robotIdentifier.textContent = displayValue(robot.identifier);

    const available = robot.control_available;

    if (available === true) {
        elements.robotControl.textContent = "Available for student code";
    } else if (available === false) {
        elements.robotControl.textContent = "Currently in use";
    } else {
        elements.robotControl.textContent = "Unknown";
    }

    setAvailabilityBadge(elements.robotControlBadge, available, {
        availableLabel: "Available",
        unavailableLabel: "In Use",
    });

    setAvailabilityBadge(elements.featureRobotControl, available, {
        availableLabel: "Available",
        unavailableLabel: "In Use",
    });
}
