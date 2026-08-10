"use strict";

export const MEDIA_API_URL = "/api/media";

export const MEDIA_UPLOAD_API_URL = "/api/media/upload";

export const MAX_UPLOAD_FILES = 10;

export const MAX_UPLOAD_FILE_SIZE = 25 * 1024 * 1024;

export const UPLOAD_EXTENSIONS = new Set([
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp3",
    ".wav",
    ".ogg",
    ".m4a",
]);

export const VIDEO_EXTENSIONS = new Set([".mp4", ".webm"]);

export const CATEGORY_LABELS = Object.freeze({
    pictures: "Picture",
    videos: "Video",
    sounds: "Sound",
});
