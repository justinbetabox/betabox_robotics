"use strict";

function setupLoginModal() {
    const modal = document.querySelector("#launchpad-login-modal");

    if (!(modal instanceof HTMLDialogElement)) {
        return;
    }

    const openButtons = document.querySelectorAll("[data-login-open]");

    const closeButtons = modal.querySelectorAll("[data-login-close]");

    const returnToInputs = modal.querySelectorAll("[data-return-to]");

    let opener = null;

    const openModal = (button = null) => {
        if (button instanceof HTMLElement) {
            opener = button;
        }

        if (!modal.open) {
            modal.showModal();
        }
    };

    const closeModal = () => {
        if (modal.open) {
            modal.close();
        }
    };

    const returnUrl = new URL(window.location.href);

    returnUrl.searchParams.delete("login");

    const currentLocation =
        returnUrl.pathname + returnUrl.search + returnUrl.hash;

    returnToInputs.forEach((input) => {
        if (input instanceof HTMLInputElement) {
            input.value = currentLocation;
        }
    });

    openButtons.forEach((button) => {
        button.addEventListener("click", () => {
            openModal(button);
        });
    });

    closeButtons.forEach((button) => {
        button.addEventListener("click", closeModal);
    });

    modal.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });

    modal.addEventListener("close", () => {
        if (opener instanceof HTMLElement) {
            opener.focus();
        }

        opener = null;
    });

    const query = new URLSearchParams(window.location.search);

    if (query.get("login") === "failed") {
        openModal();
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupLoginModal, {
        once: true,
    });
} else {
    setupLoginModal();
}
