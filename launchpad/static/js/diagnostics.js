"use strict";

import { initializeDiagnosticsPage } from "./diagnostics/page.js";

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeDiagnosticsPage, {
        once: true,
    });
} else {
    initializeDiagnosticsPage();
}
