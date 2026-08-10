"use strict";

import { elements } from "./dom.js";

import {
    categoryLabel,
    healthClass,
    serviceCardClass,
    startupLabel,
    stateLabel,
} from "./helpers.js";

/* Metadata */

function createMetaItem(label, value) {
    const item = document.createElement("div");

    item.className = "detail-card";

    const itemLabel = document.createElement("span");

    itemLabel.className = "detail-label";

    itemLabel.textContent = label;

    const itemValue = document.createElement("strong");

    itemValue.className = "detail-value";

    itemValue.textContent = value;

    item.append(itemLabel, itemValue);

    return item;
}

/* Service cards */

function createServiceCard(service) {
    const article = document.createElement("article");

    article.className = ["service-card", serviceCardClass(service.health)].join(
        " ",
    );

    const header = document.createElement("div");

    header.className = "service-card-header";

    const identity = document.createElement("div");

    identity.className = "service-card-identity";

    const indicator = document.createElement("span");

    indicator.className = ["status-dot", healthClass(service.health)].join(" ");

    indicator.setAttribute("aria-hidden", "true");

    const titleGroup = document.createElement("div");

    const title = document.createElement("h3");

    title.textContent =
        service.display_name ||
        service.name ||
        service.unit ||
        "Unknown Service";

    const unit = document.createElement("p");

    unit.className = "service-unit";

    unit.textContent = service.unit || "Unknown unit";

    titleGroup.append(title, unit);

    identity.append(indicator, titleGroup);

    const state = document.createElement("span");

    state.className = [
        "service-state-badge",
        `service-state-${service.state || "unknown"}`,
    ].join(" ");

    state.textContent = stateLabel(service.state);

    header.append(identity, state);

    const description = document.createElement("p");

    description.className = "service-description";

    description.textContent =
        service.description || "No description is available.";

    const meta = document.createElement("div");

    meta.className = "service-meta";

    meta.append(
        createMetaItem("Type", categoryLabel(service.category)),
        createMetaItem("Startup", startupLabel(service.startup)),
        createMetaItem("Installed", service.installed ? "Yes" : "No"),
    );

    article.append(header, description, meta);

    return article;
}

/* Service list */

export function renderServices(services) {
    elements.servicesList.replaceChildren();

    if (!Array.isArray(services) || services.length === 0) {
        const placeholder = document.createElement("p");

        placeholder.className = "empty-state";

        placeholder.textContent = "No managed services were found.";

        elements.servicesList.append(placeholder);

        return;
    }

    for (const service of services) {
        elements.servicesList.append(createServiceCard(service));
    }
}
