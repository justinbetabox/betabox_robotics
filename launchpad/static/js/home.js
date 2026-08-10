"use strict";

import { initializeHomePage } from "./home/page.js";

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeHomePage, {
        once: true,
    });
} else {
    initializeHomePage();
}
