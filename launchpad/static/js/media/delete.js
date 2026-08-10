"use strict";

import { elements } from "./dom.js";

import { errorMessage } from "./helpers.js";

import { state } from "./state.js";

import { announce, responseErrorMessage } from "./utils.js";

export function openDeleteDialog(file) {
    state.deleteFile = file;

    elements.deleteName.textContent = file.name;

    elements.deleteError.textContent = "";

    elements.deleteError.hidden = true;

    elements.deleteConfirmButton.disabled = false;

    elements.deleteConfirmButton.textContent = "Delete File";

    elements.deleteDialog.showModal();
}

export function resetDeleteDialog() {
    state.deleteFile = null;

    elements.deleteError.textContent = "";

    elements.deleteError.hidden = true;
}

export function closeDeleteDialog() {
    if (elements.deleteDialog.open) {
        elements.deleteDialog.close();
    }

    resetDeleteDialog();
}

export async function deleteSelectedFile({ reloadMedia } = {}) {
    const file = state.deleteFile;

    if (file === null) {
        return;
    }

    elements.deleteConfirmButton.disabled = true;

    elements.deleteConfirmButton.textContent = "Deleting…";

    elements.deleteError.hidden = true;

    elements.deleteError.textContent = "";

    try {
        const response = await fetch(file.url, {
            method: "DELETE",
            headers: {
                Accept: "application/json",
            },
        });

        if (!response.ok) {
            throw new Error(
                await responseErrorMessage(
                    response,
                    "The media file could not be deleted.",
                ),
            );
        }

        closeDeleteDialog();

        announce(`${file.name} was deleted.`);

        if (typeof reloadMedia === "function") {
            await reloadMedia({
                announceResult: false,
            });
        }
    } catch (error) {
        elements.deleteError.textContent = errorMessage(
            error,
            "The media file could not be deleted.",
        );

        elements.deleteError.hidden = false;
    } finally {
        elements.deleteConfirmButton.disabled = false;

        elements.deleteConfirmButton.textContent = "Delete File";
    }
}
