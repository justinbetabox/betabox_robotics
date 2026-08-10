"use strict";

import { initializeJupyterPage } from "./jupyter/page.js";

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeJupyterPage, {
        once: true,
    });
} else {
    initializeJupyterPage();
}
