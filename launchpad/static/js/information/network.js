"use strict";

import { elements } from "./dom.js";

/* Copy helpers */

async function copyText(value, button) {
    const originalLabel = button.textContent;

    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(value);
        } else {
            const textarea = document.createElement("textarea");

            textarea.value = value;

            textarea.setAttribute("readonly", "");

            textarea.style.position = "fixed";

            textarea.style.opacity = "0";

            textarea.style.pointerEvents = "none";

            document.body.append(textarea);

            textarea.select();

            textarea.setSelectionRange(0, textarea.value.length);

            const copied = document.execCommand("copy");

            textarea.remove();

            if (!copied) {
                throw new Error("Browser copy command failed.");
            }
        }

        button.textContent = "Copied";

        window.setTimeout(() => {
            button.textContent = originalLabel;
        }, 1500);
    } catch (error) {
        console.error("Unable to copy URL:", error);

        button.textContent = "Select";

        const link = button.closest(".url-item")?.querySelector("a");

        if (link !== null && link !== undefined) {
            const selection = window.getSelection();

            const range = document.createRange();

            range.selectNodeContents(link);

            selection?.removeAllRanges();

            selection?.addRange(range);
        }

        window.setTimeout(() => {
            button.textContent = originalLabel;
        }, 1800);
    }
}

/* Value lists */

function createValueItem(value) {
    const item = document.createElement("span");

    item.className = "value-chip";

    item.textContent = String(value);

    return item;
}

function renderValueList(container, values) {
    container.replaceChildren();

    if (!Array.isArray(values) || values.length === 0) {
        container.textContent = "Not available";

        return;
    }

    for (const value of values) {
        container.append(createValueItem(value));
    }
}

/* URL lists */

function createUrlItem(value) {
    const item = document.createElement("div");

    item.className = "url-item";

    const link = document.createElement("a");

    link.href = value;

    link.textContent = value;

    link.target = "_blank";

    link.rel = "noopener noreferrer";

    const copyButton = document.createElement("button");

    copyButton.className = "url-copy-button";

    copyButton.type = "button";

    copyButton.textContent = "Copy";

    copyButton.addEventListener("click", () => {
        void copyText(value, copyButton);
    });

    item.append(link, copyButton);

    return item;
}

function renderUrlList(container, values) {
    container.replaceChildren();

    if (!Array.isArray(values) || values.length === 0) {
        container.textContent = "Not available";

        return;
    }

    for (const value of values) {
        container.append(createUrlItem(String(value)));
    }
}

/* Network */

export function renderNetwork(network) {
    elements.networkHostname.textContent = network.hostname ?? "Not available";

    renderValueList(elements.ipAddresses, network.ip_addresses);

    renderUrlList(elements.launchpadUrls, network.launchpad_urls);

    renderUrlList(elements.jupyterhubUrls, network.jupyterhub_urls);

    renderUrlList(elements.visionUrls, network.vision_urls);
}
