const TOKEN_KEY = "is601.jwt";

function getTokenPreview(token) {
    if (!token) {
        return "No token stored yet.";
    }

    if (token.length <= 32) {
        return token;
    }

    return `${token.slice(0, 18)}...${token.slice(-12)}`;
}

function setMessage(messageElement, text, state) {
    if (!messageElement) {
        return;
    }

    messageElement.textContent = text;
    messageElement.dataset.state = state;
}

function parseInputs(rawValue) {
    const values = rawValue
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
        .map((item) => Number(item));

    if (values.length < 2 || values.some((value) => Number.isNaN(value))) {
        return null;
    }

    return values;
}

function getAuthToken() {
    return window.localStorage.getItem(TOKEN_KEY);
}

function getAuthHeaders(token) {
    return {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
    };
}

function formatResultItem(item) {
    const inputsText = Array.isArray(item.inputs) ? item.inputs.join(", ") : "";
    return `${item.type}(${inputsText}) = ${item.result}`;
}

function renderResults(items, listElement) {
    listElement.innerHTML = "";

    if (!Array.isArray(items) || items.length === 0) {
        const emptyItem = document.createElement("li");
        emptyItem.className = "result-empty";
        emptyItem.textContent = "No calculations yet.";
        listElement.appendChild(emptyItem);
        return;
    }

    items.forEach((item) => {
        const listItem = document.createElement("li");
        listItem.className = "result-item";
        listItem.dataset.id = item.id;

        const textSpan = document.createElement("span");
        textSpan.className = "result-text";
        textSpan.textContent = formatResultItem(item);

        const controls = document.createElement("div");
        controls.className = "result-controls";

        const viewBtn = document.createElement("button");
        viewBtn.type = "button";
        viewBtn.className = "tiny-button";
        viewBtn.textContent = "View";
        viewBtn.addEventListener("click", async () => {
            await handleViewCalculation(item.id);
        });

        const editBtn = document.createElement("button");
        editBtn.type = "button";
        editBtn.className = "tiny-button";
        editBtn.textContent = "Edit";
        editBtn.addEventListener("click", () => {
            handleEditCalculation(item);
        });

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "tiny-button danger";
        deleteBtn.textContent = "Delete";
        deleteBtn.addEventListener("click", async () => {
            await handleDeleteCalculation(item.id);
        });

        controls.appendChild(viewBtn);
        controls.appendChild(editBtn);
        controls.appendChild(deleteBtn);

        listItem.appendChild(textSpan);
        listItem.appendChild(controls);
        listElement.appendChild(listItem);
    });
}

async function handleViewCalculation(id) {
    const messageElement = document.querySelector("[data-message]");
    const token = getAuthToken();
    if (!token) {
        window.location.href = "/login";
        return;
    }

    const response = await fetch(`/calculations/${id}`, {
        method: "GET",
        headers: getAuthHeaders(token),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        const detail = payload?.detail || "Unable to load calculation.";
        setMessage(messageElement, detail, "error");
        return;
    }

    const inputsText = Array.isArray(payload.inputs) ? payload.inputs.join(", ") : "";
    setMessage(messageElement, `Calculation: ${payload.type}(${inputsText}) = ${payload.result}`, "info");
}

function handleEditCalculation(item) {
    const form = document.querySelector("[data-calc-form]");
    form.elements.type.value = item.type;
    form.elements.inputs.value = Array.isArray(item.inputs) ? item.inputs.join(", ") : "";
    form.dataset.editId = item.id;
    const messageElement = document.querySelector("[data-message]");
    setMessage(messageElement, "Editing calculation — submit to save changes.", "info");
}

async function handleDeleteCalculation(id) {
    const messageElement = document.querySelector("[data-message]");
    const listElement = document.querySelector("[data-result-list]");
    const token = getAuthToken();
    if (!token) {
        window.location.href = "/login";
        return;
    }

    if (!confirm("Delete this calculation?")) {
        return;
    }

    const response = await fetch(`/calculations/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(token),
    });

    if (response.status === 204) {
        setMessage(messageElement, "Calculation deleted.", "success");
        await loadCalculations(token, listElement, messageElement, true);
        await loadReport(token);
        return;
    }

    const payload = await response.json().catch(() => ({}));
    const detail = Array.isArray(payload?.detail)
        ? payload.detail[0]?.msg || "Unable to delete calculation."
        : payload?.detail || "Unable to delete calculation.";
    setMessage(messageElement, detail, "error");
}

async function loadCalculations(token, listElement, messageElement, suppressSuccessMessage = false) {
    const response = await fetch("/calculations", {
        method: "GET",
        headers: getAuthHeaders(token),
    });

    const payload = await response.json().catch(() => []);

    if (!response.ok) {
        const detail = payload?.detail || "Unable to load calculations.";
        setMessage(messageElement, detail, "error");
        if (response.status === 401) {
            window.localStorage.removeItem(TOKEN_KEY);
            window.location.href = "/login";
        }
        return;
    }

    renderResults(payload, listElement);
    if (!suppressSuccessMessage) {
        setMessage(messageElement, "Dashboard refreshed.", "success");
    }
}

async function handleCalculationSubmit(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const listElement = document.querySelector("[data-result-list]");
    const messageElement = document.querySelector("[data-message]");
    const token = getAuthToken();

    if (!token) {
        window.location.href = "/login";
        return;
    }

    const type = form.elements.type.value;
    const parsedInputs = parseInputs(form.elements.inputs.value);

    if (!parsedInputs) {
        setMessage(messageElement, "Enter at least two numeric inputs separated by commas.", "error");
        return;
    }

    setMessage(messageElement, "Submitting calculation...", "loading");

    const editId = form.dataset.editId;
    const url = editId ? `/calculations/${editId}` : "/calculations";
    const method = editId ? "PUT" : "POST";

    const response = await fetch(url, {
        method,
        headers: getAuthHeaders(token),
        body: JSON.stringify({ type, inputs: parsedInputs }),
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
        const detail = Array.isArray(payload?.detail)
            ? payload.detail[0]?.msg || "Unable to create calculation."
            : payload?.detail || "Unable to create calculation.";
        setMessage(messageElement, detail, "error");
        if (response.status === 401) {
            window.localStorage.removeItem(TOKEN_KEY);
            window.location.href = "/login";
        }
        return;
    }

    const verb = editId ? "updated" : "created";
    setMessage(messageElement, `Calculation ${verb}: ${payload.result}`, "success");
    form.reset();
    if (form.dataset.editId) {
        delete form.dataset.editId;
    }
    await loadCalculations(token, listElement, messageElement, true);
    await loadReport(token);
}

async function loadReport(token) {
    const listElement = document.querySelector("[data-report-list]");
    if (!listElement) return;

    const response = await fetch("/reports", {
        method: "GET",
        headers: getAuthHeaders(token),
    });

    if (!response.ok) return;

    const report = await response.json().catch(() => null);
    if (!report) return;

    listElement.innerHTML = "";

    if (report.total_calculations === 0) {
        const emptyItem = document.createElement("li");
        emptyItem.className = "result-empty";
        emptyItem.textContent = "No calculations yet.";
        listElement.appendChild(emptyItem);
        return;
    }

    const stats = [
        `Total: ${report.total_calculations}`,
        `Most used: ${report.most_used_type ?? "—"}`,
        `Average result: ${report.average_result != null ? report.average_result.toFixed(2) : "—"}`,
        ...report.by_type.map((s) => `${s.type}: ${s.count}`),
    ];

    stats.forEach((text) => {
        const item = document.createElement("li");
        item.className = "result-item";
        item.textContent = text;
        listElement.appendChild(item);
    });
}

function bindDashboard() {
    const tokenElement = document.querySelector("[data-token-value]");
    const form = document.querySelector("[data-calc-form]");
    const listElement = document.querySelector("[data-result-list]");
    const messageElement = document.querySelector("[data-message]");
    const refreshButton = document.querySelector("[data-refresh]");
    const refreshReportButton = document.querySelector("[data-refresh-report]");
    const logoutButton = document.querySelector("[data-logout]");

    const token = getAuthToken();
    if (!token) {
        window.location.href = "/login";
        return;
    }

    tokenElement.textContent = getTokenPreview(token);

    form.addEventListener("submit", handleCalculationSubmit);

    refreshButton.addEventListener("click", async () => {
        await loadCalculations(token, listElement, messageElement);
    });

    if (refreshReportButton) {
        refreshReportButton.addEventListener("click", async () => {
            await loadReport(token);
        });
    }

    logoutButton.addEventListener("click", () => {
        window.localStorage.removeItem(TOKEN_KEY);
        window.location.href = "/login";
    });

    loadCalculations(token, listElement, messageElement);
    loadReport(token);
}

document.addEventListener("DOMContentLoaded", bindDashboard);
