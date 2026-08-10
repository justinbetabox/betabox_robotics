"use strict";

import { initializeEventsPage } from "./events/page.js";

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeEventsPage, {
        once: true,
    });
} else {
    initializeEventsPage();
}
