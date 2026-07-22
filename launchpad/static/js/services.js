"use strict";


/* Constants */

const SERVICES_API_URL = "/api/services";
const REFRESH_INTERVAL_MS = 30000;


/* Page state */

let requestInProgress = false;
let refreshTimer = null;


/* DOM helpers */

const elements = {
    connection: document.getElementById(
        "services-connection"
    ),

    refreshButton: document.getElementById(
        "refresh-services"
    ),

    retryButton: document.getElementById(
        "retry-services"
    ),

    updated: document.getElementById(
        "services-updated"
    ),

    overallIndicator: document.getElementById(
        "overall-indicator"
    ),

    overallStatus: document.getElementById(
        "overall-status"
    ),

    healthyCount: document.getElementById(
        "healthy-count"
    ),

    warningCount: document.getElementById(
        "warning-count"
    ),

    errorCount: document.getElementById(
        "error-count"
    ),

    unknownCount: document.getElementById(
        "unknown-count"
    ),

    totalCount: document.getElementById(
        "total-count"
    ),

    attentionSection: document.getElementById(
        "attention-section"
    ),

    attentionList: document.getElementById(
        "attention-list"
    ),

    servicesList: document.getElementById(
        "services-list"
    ),

    errorPanel: document.getElementById(
        "services-error-panel"
    ),

    errorMessage: document.getElementById(
        "services-error-message"
    ),
};


/* Formatting */

function formatTimestamp(
    date
) {
    return new Intl.DateTimeFormat(
        undefined,
        {
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit",
        }
    ).format(date);
}

function formatLabel(
    value
) {
    if (!value) {
        return "Unknown";
    }

    return String(value)
        .replaceAll("-", " ")
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            character => character.toUpperCase()
        );
}

function stateLabel(
    state
) {
    const labels = {
        running: "Running",
        completed: "Completed",
        waiting: "Waiting",
        starting: "Starting",
        stopping: "Stopping",
        reloading: "Reloading",
        inactive: "Inactive",
        failed: "Failed",
        "not-installed": "Not Installed",
        unknown: "Unknown",
    };

    return labels[state] || formatLabel(state);
}

function startupLabel(
    startup
) {
    const labels = {
        continuous: "Continuous",
        oneshot: "One-Time Startup",
        conditional: "Conditional",
    };

    return (
        labels[startup]
        || formatLabel(startup)
    );
}

function categoryLabel(
    category
) {
    const labels = {
        boot: "Boot Service",
        background: "Background Service",
        web: "Web Service",
        network: "Network Service",
    };

    return (
        labels[category]
        || formatLabel(category)
    );
}


/* Classification */

function healthClass(
    health
) {
    if (health === "healthy") {
        return "status-healthy";
    }

    if (health === "warning") {
        return "status-warning";
    }

    if (health === "error") {
        return "status-error";
    }

    return "status-unknown";
}

function serviceCardClass(
    health
) {
    if (health === "healthy") {
        return "service-card-healthy";
    }

    if (health === "warning") {
        return "service-card-warning";
    }

    if (health === "error") {
        return "service-card-error";
    }

    return "service-card-unknown";
}

function overallState(
    summary
) {
    const errorCount = Number(
        summary.error || 0
    );

    const warningCount = Number(
        summary.warning || 0
    );

    const unknownCount = Number(
        summary.unknown || 0
    );

    if (errorCount > 0) {
        return {
            label: "Critical",
            className: "status-error",
        };
    }

    if (
        warningCount > 0
        || unknownCount > 0
    ) {
        return {
            label: "Needs Attention",
            className: "status-warning",
        };
    }

    return {
        label: "Healthy",
        className: "status-healthy",
    };
}

function serviceNeedsAttention(
    service
) {
    return (
        service.health === "error"
        || service.health === "warning"
        || service.health === "unknown"
    );
}

function attentionMessage(
    service
) {
    if (service.state === "failed") {
        return (
            `${service.display_name} encountered `
            + "an error."
        );
    }

    if (service.state === "not-installed") {
        return (
            `${service.display_name} is not `
            + "installed."
        );
    }

    if (service.state === "inactive") {
        return (
            `${service.display_name} is not `
            + "running."
        );
    }

    if (
        service.state === "starting"
        || service.state === "stopping"
        || service.state === "reloading"
    ) {
        return (
            `${service.display_name} is currently `
            + `${stateLabel(service.state).toLowerCase()}.`
        );
    }

    return (
        `${service.display_name} has an `
        + "unknown service state."
    );
}


/* UI helpers */

function updateTimestamp() {
    elements.updated.textContent = (
        `Updated ${formatTimestamp(new Date())}`
    );
}

function clearTimestamp() {
    elements.updated.textContent =
        "Service status unavailable";
}

function setConnectionState(
    state,
    label
) {
    const connection = elements.connection;

    connection.classList.remove(
        "status-connecting",
        "status-connected",
        "status-error"
    );

    if (state === "connected") {
        connection.classList.add(
            "status-connected"
        );
    } else if (state === "error") {
        connection.classList.add(
            "status-error"
        );
    } else {
        connection.classList.add(
            "status-connecting"
        );
    }

    connection.textContent = label;
}

function setLoadingState(
    loading
) {
    elements.refreshButton.disabled = loading;
    elements.retryButton.disabled = loading;

    elements.refreshButton.textContent = (
        loading
            ? "Refreshing…"
            : "Refresh"
    );

    if (loading) {
        setConnectionState(
            "connecting",
            "Loading…"
        );
    }
}

function showError(
    message
) {
    elements.errorMessage.textContent = (
        message
    );

    elements.errorPanel.hidden = false;

    setConnectionState(
        "error",
        "Unavailable"
    );
}

function hideError() {
    elements.errorPanel.hidden = true;
}


/* Rendering */

function renderOverview(
    summary
) {
    const overall = overallState(
        summary
    );

    elements.overallStatus.textContent = (
        overall.label
    );

    elements.overallIndicator.classList.remove(
        "status-healthy",
        "status-warning",
        "status-error",
        "status-unknown"
    );

    elements.overallIndicator.classList.add(
        overall.className
    );

    elements.healthyCount.textContent = (
        summary.healthy ?? 0
    );

    elements.warningCount.textContent = (
        summary.warning ?? 0
    );

    elements.errorCount.textContent = (
        summary.error ?? 0
    );

    elements.unknownCount.textContent = (
        summary.unknown ?? 0
    );

    elements.totalCount.textContent = (
        summary.total ?? 0
    );
}

function createMetaItem(
    label,
    value
) {
    const item = document.createElement(
        "div"
    );

    item.className = "detail-card";

    const itemLabel = document.createElement(
        "span"
    );

    itemLabel.className = (
        "detail-label"
    );

    itemLabel.textContent = label;

    const itemValue = document.createElement(
        "strong"
    );

    itemValue.className = (
        "detail-value"
    );

    itemValue.textContent = value;

    item.append(
        itemLabel,
        itemValue
    );

    return item;
}

function createServiceCard(
    service
) {
    const article = document.createElement(
        "article"
    );

    article.className = [
        "service-card",
        serviceCardClass(
            service.health
        ),
    ].join(" ");

    const header = document.createElement(
        "div"
    );

    header.className = "service-card-header";

    const identity = document.createElement(
        "div"
    );

    identity.className = (
        "service-card-identity"
    );

    const indicator = document.createElement(
        "span"
    );

    indicator.className = [
        "status-dot",
        healthClass(service.health),
    ].join(" ");

    indicator.setAttribute(
        "aria-hidden",
        "true"
    );

    const titleGroup = document.createElement(
        "div"
    );

    const title = document.createElement(
        "h3"
    );

    title.textContent = (
        service.display_name
        || service.name
        || service.unit
        || "Unknown Service"
    );

    const unit = document.createElement(
        "p"
    );

    unit.className = "service-unit";
    unit.textContent = (
        service.unit || "Unknown unit"
    );

    titleGroup.append(
        title,
        unit
    );

    identity.append(
        indicator,
        titleGroup
    );

    const state = document.createElement(
        "span"
    );

    state.className = [
        "service-state-badge",
        `service-state-${service.state || "unknown"}`,
    ].join(" ");

    state.textContent = stateLabel(
        service.state
    );

    header.append(
        identity,
        state
    );

    const description = document.createElement(
        "p"
    );

    description.className = (
        "service-description"
    );

    description.textContent = (
        service.description
        || "No description is available."
    );

    const meta = document.createElement(
        "div"
    );

    meta.className = "service-meta";

    meta.append(
        createMetaItem(
            "Type",
            categoryLabel(
                service.category
            )
        ),
        createMetaItem(
            "Startup",
            startupLabel(
                service.startup
            )
        ),
        createMetaItem(
            "Installed",
            service.installed
                ? "Yes"
                : "No"
        )
    );

    article.append(
        header,
        description,
        meta
    );

    return article;
}

function renderServices(
    services
) {
    elements.servicesList.replaceChildren();

    if (
        !Array.isArray(services)
        || services.length === 0
    ) {
        const placeholder = document.createElement(
            "p"
        );

        placeholder.className = (
            "empty-state"
        );

        placeholder.textContent = (
            "No managed services were found."
        );

        elements.servicesList.append(
            placeholder
        );

        return;
    }

    for (const service of services) {
        elements.servicesList.append(
            createServiceCard(service)
        );
    }
}

function createAttentionItem(
    service
) {
    const item = document.createElement(
        "article"
    );

    item.className = [
        "attention-item",
        service.health === "warning"
            ? "attention-warning"
            : "attention-critical",
    ].join(" ");

    const indicator = document.createElement(
        "span"
    );

    indicator.className = [
        "status-dot",
        healthClass(service.health),
    ].join(" ");

    indicator.setAttribute(
        "aria-hidden",
        "true"
    );

    const content = document.createElement(
        "div"
    );

    const title = document.createElement(
        "strong"
    );

    title.textContent = (
        service.display_name
        || service.name
        || service.unit
    );

    const message = document.createElement(
        "p"
    );

    message.textContent = attentionMessage(
        service
    );

    content.append(
        title,
        message
    );

    item.append(
        indicator,
        content
    );

    return item;
}

function renderAttention(
    services
) {
    const attentionServices = services.filter(
        serviceNeedsAttention
    );

    elements.attentionList.replaceChildren();

    if (attentionServices.length === 0) {
        elements.attentionSection.hidden = true;
        return;
    }

    for (
        const service
        of attentionServices
    ) {
        elements.attentionList.append(
            createAttentionItem(service)
        );
    }

    elements.attentionSection.hidden = false;
}

function renderPage(payload) {
    renderOverview(
        payload.summary
    );

    renderAttention(
        payload.services
    );

    renderServices(
        payload.services
    );
}


/* Validation */

function validatePayload(
    payload
) {
    if (
        !payload
        || typeof payload !== "object"
    ) {
        throw new Error(
            "The services API returned an invalid response."
        );
    }

    if (
        !payload.summary
        || typeof payload.summary !== "object"
    ) {
        throw new Error(
            "The services response does not include a summary."
        );
    }

    if (!Array.isArray(payload.services)) {
        throw new Error(
            "The services response does not include a service list."
        );
    }
}


/* API */

async function loadServices() {
    if (requestInProgress) {
        return;
    }

    requestInProgress = true;
    setLoadingState(true);
    hideError();

    try {
        const response = await fetch(
            SERVICES_API_URL,
            {
                method: "GET",
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            }
        );

        if (!response.ok) {
            let message = (
                `Services API returned HTTP `
                + `${response.status}.`
            );

            try {
                const errorPayload = (
                    await response.json()
                );

                if (errorPayload.message) {
                    message = errorPayload.message;
                }
            } catch {
                // Preserve the HTTP error message.
            }

            throw new Error(message);
        }

        const payload = await response.json();

        validatePayload(payload);

        renderPage(payload);

        updateTimestamp();

        setConnectionState(
            "connected",
            "Live"
        );
    } catch (error) {
        console.error(
            "Unable to load services:",
            error
        );

        const message = (
            error instanceof Error
                ? error.message
                : "The services API did not respond."
        );

        showError(message);

        clearTimestamp();
    } finally {
        requestInProgress = false;
        setLoadingState(false);
    }
}


/* UI */

function setupEventListeners() {
    elements.refreshButton.addEventListener(
        "click",
        () => {
            void loadServices();
        }
    );

    elements.retryButton.addEventListener(
        "click",
        () => {
            void loadServices();
        }
    );
}


/* Refresh lifecycle */

function startAutomaticRefresh() {
    stopAutomaticRefresh();

    refreshTimer = window.setInterval(
        () => {
            void loadServices();
        },
        REFRESH_INTERVAL_MS
    );
}

function stopAutomaticRefresh() {
    if (refreshTimer === null) {
        return;
    }

    window.clearInterval(refreshTimer);
    refreshTimer = null;
}


/* Initialization */

function initializeServicesPage() {
    setupEventListeners();
    startAutomaticRefresh();
    void loadServices();
}


/* Event listeners */

if (
    document.readyState === "loading"
) {
    document.addEventListener(
        "DOMContentLoaded",
        initializeServicesPage
    );
} else {
    initializeServicesPage();
}

document.addEventListener(
    "visibilitychange",
    () => {
        if (document.hidden) {
            stopAutomaticRefresh();
            return;
        }

        startAutomaticRefresh();
        void loadServices();
    }
);

window.addEventListener(
    "beforeunload",
    stopAutomaticRefresh
);
