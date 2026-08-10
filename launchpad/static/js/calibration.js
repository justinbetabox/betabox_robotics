"use strict";

import { initializeCalibrationPage } from "./calibration/page.js";

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeCalibrationPage, {
        once: true,
    });
} else {
    initializeCalibrationPage();
}
