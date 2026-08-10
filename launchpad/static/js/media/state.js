"use strict";

export const state = {
    media: [],

    counts: {
        pictures: 0,
        videos: 0,
        sounds: 0,
    },

    totalCount: 0,
    totalSizeBytes: 0,

    category: "all",
    search: "",
    sort: "newest",
    view: "grid",

    previewFile: null,
    deleteFile: null,

    loading: false,
    uploading: false,
    hasLoadedOnce: false,
};
