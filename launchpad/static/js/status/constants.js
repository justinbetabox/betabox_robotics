"use strict";

export const STATUS_API_URL = "/api/status";

export const AUTO_REFRESH_INTERVAL_MS = 30_000;

export const SERVICE_LABELS = {
    "set-hostname-from-serial.service": "Robot Hostname",

    "betabox-boot-announce.service": "Boot Announcer",

    "betabox-monitor.service": "Health Monitor",

    "jupyterhub.service": "JupyterHub",

    "betabox-video.service": "Video Service",

    "wifi-fallback.service": "Wi-Fi Fallback",

    "betabox-launchpad.service": "Launchpad",
};
