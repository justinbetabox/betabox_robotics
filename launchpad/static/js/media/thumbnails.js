"use strict";

import { setHidden } from "./utils.js";

function showThumbnailPlaceholder(placeholder, icon, symbol) {
    if (icon !== null) {
        icon.textContent = symbol;
    }

    setHidden(placeholder, false);
}

export function configureThumbnail(
    file,
    { image, video, placeholder, placeholderIcon, playIndicator },
) {
    setHidden(image, true);

    setHidden(video, true);

    setHidden(playIndicator, true);

    const placeholderSymbol =
        file.category === "pictures"
            ? "▧"
            : file.category === "videos"
              ? "▶"
              : "♪";

    showThumbnailPlaceholder(placeholder, placeholderIcon, placeholderSymbol);

    if (file.category === "pictures" && image !== null) {
        configureImageThumbnail(file, image, placeholder, placeholderIcon);

        return;
    }

    if (file.category === "videos" && video !== null) {
        configureVideoThumbnail(
            file,
            video,
            placeholder,
            placeholderIcon,
            playIndicator,
        );

        return;
    }

    setHidden(playIndicator, false);
}

function configureImageThumbnail(file, image, placeholder, placeholderIcon) {
    image.alt = file.name;

    image.loading = "eager";

    image.decoding = "async";

    image.addEventListener(
        "load",
        () => {
            setHidden(image, false);

            setHidden(placeholder, true);
        },
        {
            once: true,
        },
    );

    image.addEventListener(
        "error",
        () => {
            image.removeAttribute("src");

            setHidden(image, true);

            showThumbnailPlaceholder(placeholder, placeholderIcon, "▧");
        },
        {
            once: true,
        },
    );

    image.src = file.url;
}

function configureVideoThumbnail(
    file,
    video,
    placeholder,
    placeholderIcon,
    playIndicator,
) {
    setHidden(playIndicator, false);

    video.addEventListener(
        "loadedmetadata",
        () => {
            if (Number.isFinite(video.duration) && video.duration > 0.1) {
                video.currentTime = Math.min(0.1, video.duration / 2);
            }
        },
        {
            once: true,
        },
    );

    video.addEventListener(
        "seeked",
        () => {
            setHidden(video, false);

            setHidden(placeholder, true);
        },
        {
            once: true,
        },
    );

    video.addEventListener(
        "loadeddata",
        () => {
            setHidden(video, false);

            setHidden(placeholder, true);
        },
        {
            once: true,
        },
    );

    video.addEventListener(
        "error",
        () => {
            video.removeAttribute("src");

            setHidden(video, true);

            showThumbnailPlaceholder(placeholder, placeholderIcon, "▶");
        },
        {
            once: true,
        },
    );

    video.src = file.url;

    video.load();
}
