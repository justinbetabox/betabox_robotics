
"use strict";

/*
 * Betabox offline clock recovery.
 *
 * Start clock synchronization early and expose its completion
 * so navigation can wait for the result when necessary.
 */

(() => {
    const controller = new AbortController();

    const timeout = window.setTimeout(() => {
        controller.abort();
    }, 15000);

    window.betaboxClockReady = fetch("/api/clock/check", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            browser_time_ms: Date.now(),
        }),
        credentials: "same-origin",
        cache: "no-store",
        signal: controller.signal,
    })
        .then(async (response) => {
            if (!response.ok) {
                return false;
            }

            const result = await response.json();

            return result.status === "ok";
        })
        .catch(() => false)
        .finally(() => {
            window.clearTimeout(timeout);
        });
})();
