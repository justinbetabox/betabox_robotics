"use strict";

import { initializeServicesPage } from "./services/page.js";

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeServicesPage, {
        once: true,
    });
} else {
    initializeServicesPage();
}
