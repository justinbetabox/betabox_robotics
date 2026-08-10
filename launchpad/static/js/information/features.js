"use strict";

import { elements } from "./dom.js";

import { setAvailabilityBadge } from "./helpers.js";

/* Platform features */

export function renderFeatures(features) {
    setAvailabilityBadge(
        elements.featureVisionService,
        features.vision_service_available,
        {
            availableLabel: "Running",
            unavailableLabel: "Unavailable",
        },
    );

    setAvailabilityBadge(elements.featureCamera, features.camera_ready, {
        availableLabel: "Ready",
        unavailableLabel: "Not Ready",
    });

    setAvailabilityBadge(
        elements.featureJupyterhub,
        features.jupyterhub_available,
        {
            availableLabel: "Installed",
            unavailableLabel: "Unavailable",
        },
    );
}

/* Media locations */

export function renderMedia(media) {
    setAvailabilityBadge(elements.mediaPictures, media.pictures_available, {
        availableLabel: "Ready",
        unavailableLabel: "Missing",
    });

    setAvailabilityBadge(elements.mediaVideos, media.videos_available, {
        availableLabel: "Ready",
        unavailableLabel: "Missing",
    });

    setAvailabilityBadge(elements.mediaSounds, media.sounds_available, {
        availableLabel: "Ready",
        unavailableLabel: "Missing",
    });
}
