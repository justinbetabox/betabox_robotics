"use strict";

function isObjectPayload(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
}

export async function requestJson(
    url,
    {
        method = "GET",
        body,
        cache,
        invalidMessage = "Calibration API returned " + "an invalid response.",
        errorMessage = "Calibration request failed.",
    } = {},
) {
    if (typeof url !== "string" || url.length === 0) {
        throw new TypeError("url must be a non-empty string");
    }

    const headers = {
        Accept: "application/json",
    };

    const options = {
        method,
        headers,
    };

    if (cache !== undefined) {
        options.cache = cache;
    }

    if (body !== undefined) {
        headers["Content-Type"] = "application/json";

        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    let payload;

    try {
        payload = await response.json();
    } catch {
        throw new Error(invalidMessage);
    }

    if (!isObjectPayload(payload)) {
        throw new Error(invalidMessage);
    }

    if (!response.ok) {
        const message =
            typeof payload.message === "string" && payload.message.trim() !== ""
                ? payload.message
                : errorMessage;

        throw new Error(message);
    }

    return payload;
}
