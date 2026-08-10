"use strict";

function requireElement(selector, expectedType = HTMLElement) {
    const found = document.querySelector(selector);

    if (!(found instanceof expectedType)) {
        throw new Error(`Missing required element: ${selector}`);
    }

    return found;
}

export const elements = {
    connection: requireElement("#information-connection"),

    refreshButton: requireElement("#refresh-information", HTMLButtonElement),

    retryButton: requireElement("#retry-information", HTMLButtonElement),

    updated: requireElement("#information-updated"),

    errorPanel: requireElement("#information-error-panel"),

    errorMessage: requireElement("#information-error-message"),

    robotModel: requireElement("#robot-model"),

    robotHostname: requireElement("#robot-hostname"),

    robotIdentifier: requireElement("#robot-identifier"),

    robotControl: requireElement("#robot-control"),

    robotControlBadge: requireElement("#robot-control-badge"),

    networkHostname: requireElement("#network-hostname"),

    ipAddresses: requireElement("#ip-addresses"),

    launchpadUrls: requireElement("#launchpad-urls"),

    jupyterhubUrls: requireElement("#jupyterhub-urls"),

    visionUrls: requireElement("#vision-urls"),

    softwareVersion: requireElement("#software-version"),

    pythonVersion: requireElement("#python-version"),

    operatingSystem: requireElement("#operating-system"),

    architecture: requireElement("#architecture"),

    storagePercent: requireElement("#storage-percent"),

    storageMeterFill: requireElement("#storage-meter-fill"),

    storageUsed: requireElement("#storage-used"),

    storageAvailable: requireElement("#storage-available"),

    storageTotal: requireElement("#storage-total"),

    featureRobotControl: requireElement("#feature-robot-control"),

    featureVisionService: requireElement("#feature-vision-service"),

    featureCamera: requireElement("#feature-camera"),

    featureJupyterhub: requireElement("#feature-jupyterhub"),

    mediaPictures: requireElement("#media-pictures"),

    mediaVideos: requireElement("#media-videos"),

    mediaSounds: requireElement("#media-sounds"),

    reducedMotion: requireElement("#reduced-motion", HTMLInputElement),

    largerText: requireElement("#larger-text", HTMLInputElement),

    compactLayout: requireElement("#compact-layout", HTMLInputElement),

    resetPreferences: requireElement("#reset-preferences", HTMLButtonElement),

    preferencesStatus: requireElement("#preferences-status"),
};
