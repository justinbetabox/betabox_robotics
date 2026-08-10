"use strict";

import { elements } from "./dom.js";

import { healthClass, stateLabel } from "./helpers.js";

/* Classification */

function serviceNeedsAttention(service) {
    return (
        service.health === "error" ||
        service.health === "warning" ||
        service.health === "unknown"
    );
}

function attentionMessage(service) {
    if (service.state === "failed") {
        return `${service.display_name} encountered an error.`;
    }

    if (service.state === "not-installed") {
        return `${service.display_name} is not installed.`;
    }

    if (service.state === "inactive") {
        return `${service.display_name} is not running.`;
    }

    if (
        service.state === "starting" ||
        service.state === "stopping" ||
        service.state === "reloading"
    ) {
        return (
            `${service.display_name} is currently ` +
            `${stateLabel(service.state).toLowerCase()}.`
        );
    }

    return `${service.display_name} has an unknown service state.`;
}

/* Rendering */

function createAttentionItem(service) {
    const item = document.createElement("article");

    item.className = [
        "attention-item",
        service.health === "warning"
            ? "attention-warning"
            : "attention-critical",
    ].join(" ");

    const indicator = document.createElement("span");

    indicator.className = ["status-dot", healthClass(service.health)].join(" ");

    indicator.setAttribute("aria-hidden", "true");

    const content = document.createElement("div");

    const title = document.createElement("strong");

    title.textContent = service.display_name;

    const message = document.createElement("p");

    message.textContent = attentionMessage(service);

    content.append(title, message);

    item.append(indicator, content);

    return item;
}

export function renderAttention(services) {
    const attentionServices = services.filter(serviceNeedsAttention);

    elements.attentionList.replaceChildren();

    if (attentionServices.length === 0) {
        elements.attentionSection.hidden = true;

        return;
    }

    for (const service of attentionServices) {
        elements.attentionList.append(createAttentionItem(service));
    }

    elements.attentionSection.hidden = false;
}
