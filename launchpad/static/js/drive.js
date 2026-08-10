"use strict";

import { initializeDrivePage } from "./drive/page.js";

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeDrivePage, {
        once: true,
    });
} else {
    initializeDrivePage();
}
