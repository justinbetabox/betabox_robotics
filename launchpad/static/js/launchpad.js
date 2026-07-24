"use strict";

function setupStudentLogin() {
    const modal = document.querySelector("#student-login-modal");

    if (!(modal instanceof HTMLDialogElement)) {
        return;
    }

    const openButtons = document.querySelectorAll("[data-login-open]");
    const closeButtons = document.querySelectorAll("[data-login-close]");
    const returnToInputs = document.querySelectorAll("[data-return-to]");

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
            modal.showModal();

            const username = modal.querySelector('input[name="username"]');

            if (username instanceof HTMLInputElement) {
                username.focus();
            }
        });
    });

    closeButtons.forEach((button) => {
        button.addEventListener("click", () => {
            modal.close();
        });
    });

    modal.addEventListener("click", (event) => {
        if (event.target === modal) {
            modal.close();
        }
    });

    const query = new URLSearchParams(window.location.search);

    if (query.get("login") === "failed" && !modal.open) {
        modal.showModal();

        const username = modal.querySelector('input[name="username"]');

        if (username instanceof HTMLInputElement) {
            username.focus();
        }
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupStudentLogin);
} else {
    setupStudentLogin();
}
