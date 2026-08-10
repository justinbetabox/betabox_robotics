"use strict";

import { CATEGORY_LABELS } from "./constants.js";

export function formatBytes(value) {
    const bytes = Number(value);

    if (!Number.isFinite(bytes) || bytes < 0) {
        return "Unknown size";
    }

    if (bytes === 0) {
        return "0 B";
    }

    const units = ["B", "KB", "MB", "GB", "TB"];

    const unitIndex = Math.min(
        Math.floor(Math.log(bytes) / Math.log(1024)),
        units.length - 1,
    );

    const amount = bytes / 1024 ** unitIndex;

    const fractionDigits = unitIndex === 0 ? 0 : amount >= 10 ? 1 : 2;

    return `${amount.toFixed(fractionDigits)} ` + units[unitIndex];
}

export function parseDate(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return null;
    }

    return date;
}

export function formatDate(value) {
    const date = parseDate(value);

    if (date === null) {
        return "Unknown date";
    }

    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date);
}

export function dateTimestamp(value) {
    const date = parseDate(value);

    return date === null ? 0 : date.getTime();
}

export function pluralize(count, singular, plural) {
    return count === 1 ? singular : plural;
}

export function categoryLabel(category) {
    return CATEGORY_LABELS[category] ?? "Media";
}

export function safeCount(value) {
    const number = Number(value);

    if (!Number.isFinite(number) || number < 0) {
        return 0;
    }

    return Math.floor(number);
}

export function filenameExtension(filename) {
    const index = filename.lastIndexOf(".");

    if (index < 0 || index === filename.length - 1) {
        return "";
    }

    return filename.slice(index).toLocaleLowerCase();
}

export function errorMessage(error, fallback) {
    if (error instanceof Error && error.message.trim() !== "") {
        return error.message;
    }

    return fallback;
}
