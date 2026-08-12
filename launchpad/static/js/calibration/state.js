"use strict";

export const state = {
    pageInitialized: false,
    pageClosing: false,

    hasLoadedOnce: false,

    steering: {
        offset: 0,
        savedOffset: 0,
        previewTimer: null,
    },

    camera: {
        panOffset: 0,
        tiltOffset: 0,
        savedPanOffset: 0,
        savedTiltOffset: 0,
        previewTimer: null,
    },

    motors: {
        leftTrim: 1,
        rightTrim: 1,
        savedLeftTrim: 1,
        savedRightTrim: 1,
    },

    grayscale: {
        calibrated: false,
        floor: null,
        line: null,
        savedFloor: null,
        savedLine: null,
    },
};
