"use strict";

import { elements } from "./dom.js";

import {
    formatEventDate,
    formatEventTime,
    severityClass,
    severityLabel,
} from "./helpers.js";

function createDetailValue(value) {
    if (value === null || value === undefined) {
        return "";
    }

    if (typeof value === "object") {
        return JSON.stringify(value, null, 2);
    }

    return String(value);
}

function createEventDetails(event) {
    const hasEventName = typeof event.event === "string" && event.event !== "";

    const hasDetails =
        event.details !== null &&
        typeof event.details === "object" &&
        !Array.isArray(event.details) &&
        Object.keys(event.details).length > 0;

    if (!hasEventName && !hasDetails) {
        return null;
    }

    const details = document.createElement("details");

    details.className = "event-details";

    const summary = document.createElement("summary");

    summary.textContent = "View event details";

    const content = document.createElement("div");

    content.className = "event-detail-content";

    if (hasEventName) {
        const row = document.createElement("div");

        row.className = "event-detail-row";

        const label = document.createElement("span");

        label.textContent = "Event";

        const value = document.createElement("code");

        value.textContent = event.event;

        row.append(label, value);

        content.append(row);
    }

    if (hasDetails) {
        const block = document.createElement("div");

        block.className = "event-detail-block";

        const label = document.createElement("span");

        label.textContent = "Details";

        const value = document.createElement("pre");

        value.textContent = createDetailValue(event.details);

        block.append(label, value);

        content.append(block);
    }

    details.append(summary, content);

    return details;
}

function createEventCard(event) {
    const article = document.createElement("article");

    article.className = ["event-card", severityClass(event.severity)].join(" ");

    const marker = document.createElement("div");

    marker.className = "event-marker";

    marker.setAttribute("aria-hidden", "true");

    const content = document.createElement("div");

    content.className = "event-content";

    const header = document.createElement("div");

    header.className = "event-header";

    const identity = document.createElement("div");

    identity.className = "event-identity";

    const component = document.createElement("h3");

    component.textContent =
        typeof event.component === "string" && event.component.trim() !== ""
            ? event.component
            : "unknown";

    const badge = document.createElement("span");

    const severity =
        typeof event.severity === "string" && event.severity !== ""
            ? event.severity
            : "info";

    badge.className = ["event-badge", `event-badge-${severity}`].join(" ");

    badge.textContent = severityLabel(severity);

    identity.append(component, badge);

    const timestamp = document.createElement("div");

    timestamp.className = "event-timestamp";

    const date = document.createElement("span");

    date.textContent = formatEventDate(event.timestamp);

    const time = document.createElement("strong");

    time.textContent = formatEventTime(event.timestamp);

    timestamp.append(date, time);

    header.append(identity, timestamp);

    const message = document.createElement("p");

    message.className = "event-message";

    message.textContent =
        typeof event.message === "string" && event.message.trim() !== ""
            ? event.message
            : "Unknown event";

    content.append(header, message);

    const details = createEventDetails(event);

    if (details !== null) {
        content.append(details);
    }

    article.append(marker, content);

    return article;
}

export function renderEvents(events, summary) {
    elements.eventsList.replaceChildren();

    if (!Array.isArray(events) || events.length === 0) {
        const empty = document.createElement("div");

        empty.className = "empty-state events-empty";

        const title = document.createElement("strong");

        title.textContent = "No matching events";

        const message = document.createElement("p");

        message.textContent =
            "Try changing the selected filters " + "or check again later.";

        empty.append(title, message);

        elements.eventsList.append(empty);

        elements.listSummary.textContent =
            "No events match the current filters";

        elements.eventsList.setAttribute("aria-busy", "false");

        return;
    }

    for (const event of events) {
        elements.eventsList.append(createEventCard(event));
    }

    const shown = Number(summary.total ?? events.length);

    const available = Number(summary.total_available ?? shown);

    if (shown < available) {
        elements.listSummary.textContent =
            `Showing ${shown} of ${available} ` + "matching events";
    } else {
        elements.listSummary.textContent = `${shown} ${
            shown === 1 ? "event" : "events"
        }`;
    }

    elements.eventsList.setAttribute("aria-busy", "false");
}
