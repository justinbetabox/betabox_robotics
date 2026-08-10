"use strict";

import { initializeInformationPage } from "./information/page.js";

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeInformationPage, {
        once: true,
    });
} else {
    initializeInformationPage();
}
