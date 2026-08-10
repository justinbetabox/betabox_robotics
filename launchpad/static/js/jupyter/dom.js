"use strict";

function requireElement(selector, expectedType = HTMLElement) {
    const element = document.querySelector(selector);

    if (!(element instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return element;
}

export const elements = {
    status: requireElement("#jupyter-status"),

    serviceState: requireElement("#jupyter-service-state"),

    httpState: requireElement("#jupyter-http-state"),

    port: requireElement("#jupyter-port"),

    openButton: requireElement("#open-jupyter", HTMLAnchorElement),

    message: requireElement("#jupyter-message"),
};
