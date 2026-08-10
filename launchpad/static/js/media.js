"use strict";

import { initializeMediaPage } from "./media/page.js";

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeMediaPage, {
        once: true,
    });
} else {
    initializeMediaPage();
}
