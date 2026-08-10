"use strict";

import { initializeStatusPage } from "./status/page.js";

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeStatusPage, {
        once: true,
    });
} else {
    initializeStatusPage();
}
