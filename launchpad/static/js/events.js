"use strict";


/* Constants */

const EVENTS_API_URL = "/api/events";
const REFRESH_INTERVAL_MS = 30000;


/* Page state */

let requestInProgress = false;
let refreshTimer = null;


/* DOM helpers */

const elements = {
    connection: document.getElementById(
        "events-connection"
    ),

    refreshButton: document.getElementById(
        "refresh-events"
    ),

    retryButton: document.getElementById(
        "retry-events"
    ),

    clearButton: document.getElementById(
        "clear-filters"
    ),

    filterForm: document.getElementById(
        "events-filter-form"
    ),

    severityFilter: document.getElementById(
        "severity-filter"
    ),

    componentFilter: document.getElementById(
        "component-filter"
    ),

    limitFilter: document.getElementById(
        "limit-filter"
    ),

    updated: document.getElementById(
        "events-updated"
    ),

    totalCount: document.getElementById(
        "total-count"
    ),

    availableCount: document.getElementById(
        "available-count"
    ),

    infoCount: document.getElementById(
        "info-count"
    ),

    warningCount: document.getElementById(
        "warning-count"
    ),

    errorCount: document.getElementById(
        "error-count"
    ),

    criticalCount: document.getElementById(
        "critical-count"
    ),

    overviewIndicator: document.getElementById(
        "events-overview-indicator"
    ),

    listSummary: document.getElementById(
        "event-list-summary"
    ),

    eventsList: document.getElementById(
        "events-list"
    ),

    errorPanel: document.getElementById(
        "events-error-panel"
    ),

    errorMessage: document.getElementById(
        "events-error-message"
    ),
};


/* Formatting */

function formatUpdatedTime(
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

function parseTimestamp(
    value
) {
    if (
        typeof value !== "string"
        || value === ""
        || value === "unknown time"
    ) {
        return null;
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return null;
    }

    return date;
}

function formatEventDate(
    value
) {
    const date = parseTimestamp(value);

    if (date === null) {
        return "Unknown date";
    }

    return new Intl.DateTimeFormat(
        undefined,
        {
            month: "short",
            day: "numeric",
            year: "numeric",
        }
    ).format(date);
}

function formatEventTime(
    value
) {
    const date = parseTimestamp(value);

    if (date === null) {
        return "Unknown time";
    }

    return new Intl.DateTimeFormat(
        undefined,
        {
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit",
        }
    ).format(date);
}


/* Classification */

function severityLabel(
    severity
) {
    const labels = {
        info: "Information",
        warning: "Warning",
        error: "Error",
        critical: "Critical",
    };

    return labels[severity] || "Information";
}

function severityClass(
    severity
) {
    if (severity === "warning") {
        return "event-warning";
    }

    if (severity === "error") {
        return "event-error";
    }

    if (severity === "critical") {
        return "event-critical";
    }

    return "event-info";
}

function overviewStatusClass(
    summary
) {
    if (
        Number(summary.critical ?? 0) > 0
        || Number(summary.error ?? 0) > 0
    ) {
        return "status-error";
    }

    if (
        Number(summary.warning ?? 0) > 0
    ) {
        return "status-warning";
    }

    return "status-info";
}


/* UI helpers */

function setConnectionState(
    state,
    label
) {
    elements.connection.classList.remove(
        "status-connecting",
        "status-connected",
        "status-error"
    );

    if (state === "connected") {
        elements.connection.classList.add(
            "status-connected"
        );
    } else if (state === "error") {
        elements.connection.classList.add(
            "status-error"
        );
    } else {
        elements.connection.classList.add(
            "status-connecting"
        );
    }

    elements.connection.textContent = label;
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
    elements.errorMessage.textContent = message;
    elements.errorPanel.hidden = false;

    setConnectionState(
        "error",
        "Unavailable"
    );
}

function hideError() {
    elements.errorPanel.hidden = true;
}

function updateTimestamp() {
    elements.updated.textContent = (
        `Updated ${formatUpdatedTime(new Date())}`
    );
}

function clearTimestamp() {
    elements.updated.textContent =
        "Events unavailable";
}


/* Rendering */

function renderOverview(
    summary
) {
    elements.totalCount.textContent = (
        summary.total ?? 0
    );

    elements.availableCount.textContent = (
        summary.total_available ?? 0
    );

    elements.infoCount.textContent = (
        summary.info ?? 0
    );

    elements.warningCount.textContent = (
        summary.warning ?? 0
    );

    elements.errorCount.textContent = (
        summary.error ?? 0
    );

    elements.criticalCount.textContent = (
        summary.critical ?? 0
    );

    elements.overviewIndicator.classList.remove(
        "status-info",
        "status-warning",
        "status-error",
        "status-unknown"
    );

    elements.overviewIndicator.classList.add(
        overviewStatusClass(summary)
    );
}

function renderLoadingState() {
    elements.updated.textContent =
        "Loading platform events…";

    elements.listSummary.textContent =
        "Loading…";

    elements.eventsList.replaceChildren();

    const loading = document.createElement(
        "div"
    );

    loading.className = "empty-state";

    loading.textContent =
        "Loading platform events…";

    elements.eventsList.append(
        loading
    );
}

function renderComponentOptions(
    components
) {
    const selectedValue = (
        elements.componentFilter.value
    );

    const defaultOption = document.createElement(
        "option"
    );

    defaultOption.value = "";
    defaultOption.textContent = "All components";

    elements.componentFilter.replaceChildren(
        defaultOption
    );

    if (!Array.isArray(components)) {
        return;
    }

    for (const component of components) {
        const option = document.createElement(
            "option"
        );

        option.value = component;
        option.textContent = component;

        elements.componentFilter.append(
            option
        );
    }

    if (
        components.includes(selectedValue)
    ) {
        elements.componentFilter.value = (
            selectedValue
        );
    }
}

function createDetailValue(
    value
) {
    if (
        value === null
        || value === undefined
    ) {
        return "";
    }

    if (typeof value === "object") {
        return JSON.stringify(
            value,
            null,
            2
        );
    }

    return String(value);
}

function createEventDetails(
    event
) {
    const hasEventName = (
        typeof event.event === "string"
        && event.event !== ""
    );

    const hasDetails = (
        event.details
        && typeof event.details === "object"
        && Object.keys(event.details).length > 0
    );

    if (!hasEventName && !hasDetails) {
        return null;
    }

    const details = document.createElement(
        "details"
    );

    details.className = "event-details";

    const summary = document.createElement(
        "summary"
    );

    summary.textContent = "View event details";

    const content = document.createElement(
        "div"
    );

    content.className = "event-detail-content";

    if (hasEventName) {
        const row = document.createElement(
            "div"
        );

        row.className = "event-detail-row";

        const label = document.createElement(
            "span"
        );

        label.textContent = "Event";

        const value = document.createElement(
            "code"
        );

        value.textContent = event.event;

        row.append(
            label,
            value
        );

        content.append(row);
    }

    if (hasDetails) {
        const block = document.createElement(
            "div"
        );

        block.className = "event-detail-block";

        const label = document.createElement(
            "span"
        );

        label.textContent = "Details";

        const value = document.createElement(
            "pre"
        );

        value.textContent = createDetailValue(
            event.details
        );

        block.append(
            label,
            value
        );

        content.append(block);
    }

    details.append(
        summary,
        content
    );

    return details;
}

function createEventCard(
    event
) {
    const article = document.createElement(
        "article"
    );

    article.className = [
        "event-card",
        severityClass(event.severity),
    ].join(" ");

    const marker = document.createElement(
        "div"
    );

    marker.className = "event-marker";

    marker.setAttribute(
        "aria-hidden",
        "true"
    );

    const content = document.createElement(
        "div"
    );

    content.className = "event-content";

    const header = document.createElement(
        "div"
    );

    header.className = "event-header";

    const identity = document.createElement(
        "div"
    );

    identity.className = "event-identity";

    const component = document.createElement(
        "h3"
    );

    component.textContent = (
        event.component || "unknown"
    );

    const badge = document.createElement(
        "span"
    );

    badge.className = [
        "event-badge",
        `event-badge-${event.severity || "info"}`,
    ].join(" ");

    badge.textContent = severityLabel(
        event.severity
    );

    identity.append(
        component,
        badge
    );

    const timestamp = document.createElement(
        "div"
    );

    timestamp.className = "event-timestamp";

    const date = document.createElement(
        "span"
    );

    date.textContent = formatEventDate(
        event.timestamp
    );

    const time = document.createElement(
        "strong"
    );

    time.textContent = formatEventTime(
        event.timestamp
    );

    timestamp.append(
        date,
        time
    );

    header.append(
        identity,
        timestamp
    );

    const message = document.createElement(
        "p"
    );

    message.className = "event-message";

    message.textContent = (
        event.message || "Unknown event"
    );

    content.append(
        header,
        message
    );

    const details = createEventDetails(
        event
    );

    if (details !== null) {
        content.append(details);
    }

    article.append(
        marker,
        content
    );

    return article;
}

function renderEvents(
    events,
    summary
) {
    elements.eventsList.replaceChildren();

    if (
        !Array.isArray(events)
        || events.length === 0
    ) {
        const empty = document.createElement(
            "div"
        );

        empty.className = "empty-state events-empty";

        empty.innerHTML = `
            <strong>No matching events</strong>
            <p>
                Try changing the selected filters
                or check again later.
            </p>
        `;

        elements.eventsList.append(empty);

        elements.listSummary.textContent = (
            "No events match the current filters"
        );

        return;
    }

    for (const event of events) {
        elements.eventsList.append(
            createEventCard(event)
        );
    }

    const shown = summary.total ?? events.length;
    const available = (
        summary.total_available ?? shown
    );

    if (shown < available) {
        elements.listSummary.textContent = (
            `Showing ${shown} of ${available} `
            + "matching events"
        );
    } else {
        elements.listSummary.textContent = (
            `${shown} ${
                shown === 1
                    ? "event"
                    : "events"
            }`
        );
    }
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
            "The Events API returned an invalid response."
        );
    }

    if (
        !payload.summary
        || typeof payload.summary !== "object"
    ) {
        throw new Error(
            "The event response does not include a summary."
        );
    }

    if (!Array.isArray(payload.events)) {
        throw new Error(
            "The event response does not include events."
        );
    }
}


/* API */

function buildApiUrl() {
    const params = new URLSearchParams();

    const severity = (
        elements.severityFilter.value
    );

    const component = (
        elements.componentFilter.value
    );

    const last = (
        elements.limitFilter.value
    );

    if (severity !== "") {
        params.set(
            "severity",
            severity
        );
    }

    if (component !== "") {
        params.set(
            "component",
            component
        );
    }

    params.set(
        "last",
        last
    );

    return `${EVENTS_API_URL}?${params}`;
}

async function loadEvents() {
    if (requestInProgress) {
        return;
    }

    requestInProgress = true;

    setLoadingState(true);
    hideError();

    renderLoadingState();

    try {
        const response = await fetch(
            buildApiUrl(),
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
                `Events API returned HTTP `
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
                // Keep the HTTP error message.
            }

            throw new Error(message);
        }

        const payload = await response.json();

        validatePayload(payload);

        renderOverview(
            payload.summary
        );

        renderComponentOptions(
            payload.components
        );

        renderEvents(
            payload.events,
            payload.summary
        );

        updateTimestamp();

        setConnectionState(
            "connected",
            "Live"
        );
    } catch (error) {
        console.error(
            "Unable to load events:",
            error
        );

        const message = (
            error instanceof Error
                ? error.message
                : "The Events API did not respond."
        );

        showError(message);

        clearTimestamp();
    } finally {
        requestInProgress = false;
        setLoadingState(false);
    }
}


/* UI */

function clearFilters() {
    elements.severityFilter.value = "";
    elements.componentFilter.value = "";
    elements.limitFilter.value = "50";

    void loadEvents();
}

function setupEventListeners() {
    elements.refreshButton.addEventListener(
        "click",
        () => {
            void loadEvents();
        }
    );

    elements.retryButton.addEventListener(
        "click",
        () => {
            void loadEvents();
        }
    );

    elements.clearButton.addEventListener(
        "click",
        () => {
            void clearFilters();
        }
    );

    elements.filterForm.addEventListener(
        "submit",
        event => {
            event.preventDefault();

            void loadEvents();
        }
    );
}


/* Refresh lifecycle */

function startAutomaticRefresh() {
    stopAutomaticRefresh();

    refreshTimer = window.setInterval(
        () => {
            void loadEvents();
        },
        REFRESH_INTERVAL_MS
    );
}

function stopAutomaticRefresh() {
    if (refreshTimer === null) {
        return;
    }

    window.clearInterval(
        refreshTimer
    );

    refreshTimer = null;
}


/* Initialization */

function initializeEventsPage() {
    setupEventListeners();

    startAutomaticRefresh();

    void loadEvents();
}


/* Event listeners */

if (
    document.readyState === "loading"
) {
    document.addEventListener(
        "DOMContentLoaded",
        initializeEventsPage
    );
} else {
    initializeEventsPage();
}

document.addEventListener(
    "visibilitychange",
    () => {
        if (document.hidden) {
            stopAutomaticRefresh();
            return;
        }

        startAutomaticRefresh();
        void loadEvents();
    }
);

window.addEventListener(
    "beforeunload",
    stopAutomaticRefresh
);
