const API_BASE = "http://127.0.0.1:8000";

let token = localStorage.getItem("imran_access_token");
let currentSection = "dashboard";

const sections = {
    sales: {
        title: "Sales",
        endpoint: "/api/v1/sales"
    },
    purchases: {
        title: "Purchases",
        endpoint: "/api/v1/purchases"
    },
    inventory: {
        title: "Inventory",
        endpoint: "/api/v1/products"
    },
    customers: {
        title: "Customers",
        endpoint: "/api/v1/customers"
    },
    suppliers: {
        title: "Suppliers",
        endpoint: "/api/v1/suppliers"
    },
    employees: {
        title: "Employees",
        endpoint: "/api/v1/employees"
    },
    services: {
        title: "Services",
        endpoint: "/api/v1/services"
    },
    appointments: {
        title: "Appointments",
        endpoint: "/api/v1/appointments"
    },
    invoices: {
        title: "Invoices",
        endpoint: "/api/v1/invoices"
    },
    notifications: {
        title: "Notifications",
        endpoint: "/api/v1/notifications"
    }
};

const $ = id => document.getElementById(id);

async function api(path, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(API_BASE + path, {
        ...options,
        headers
    });

    if (response.status === 401) {
        logout();
        throw new Error("Authentication expired.");
    }

    const text = await response.text();

    let data;
    try {
        data = text ? JSON.parse(text) : null;
    } catch {
        data = text;
    }

    if (!response.ok) {
        const message =
            typeof data === "object" && data?.detail
                ? data.detail
                : `HTTP ${response.status}`;

        throw new Error(message);
    }

    return data;
}

function extractRecords(data) {
    if (Array.isArray(data)) return data;

    if (data && Array.isArray(data.items)) return data.items;
    if (data && Array.isArray(data.results)) return data.results;
    if (data && Array.isArray(data.data)) return data.data;

    return [];
}

async function login(email, password) {
    const data = await api("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
    });

    const accessToken =
        data?.access_token ||
        data?.token ||
        data?.accessToken;

    if (!accessToken) {
        throw new Error("Login succeeded but no access token was returned.");
    }

    token = accessToken;
    localStorage.setItem("imran_access_token", token);

    return data;
}

function logout() {
    token = null;
    localStorage.removeItem("imran_access_token");

    $("appScreen").classList.add("hidden");
    $("loginScreen").classList.remove("hidden");
}

let dashboardLoading = false;

async function loadDashboard() {
    if (dashboardLoading) {
        console.log("Dashboard load already running; skipping duplicate request.");
        return;
    }

    dashboardLoading = true;

    try {
    $("connectionStatus").textContent = "Loading business data...";

    const requests = await Promise.allSettled([
        api("/api/v1/customers"),
        api("/api/v1/products"),
        api("/api/v1/employees"),
        api("/api/v1/services"),
        api("/api/v1/invoices"),
        api("/api/v1/notifications"),
        api("/api/v1/sales"),
        api("/api/v1/purchases")
    ]);

    const [
        customers,
        products,
        employees,
        services,
        invoices,
        notifications,
        sales,
        purchases
    ] = requests.map(result =>
        result.status === "fulfilled"
            ? extractRecords(result.value)
            : []
    );

    $("customersCount").textContent = customers.length;
    $("productsCount").textContent = products.length;
    $("employeesCount").textContent = employees.length;
    $("servicesCount").textContent = services.length;
    $("invoicesCount").textContent = invoices.length;
    $("notificationsCount").textContent = notifications.length;

    const activity = [];

    if (sales.length) {
        activity.push({
            title: `${sales.length} sales recorded`,
            meta: "Sales"
        });
    }

    if (purchases.length) {
        activity.push({
            title: `${purchases.length} purchases recorded`,
            meta: "Purchasing"
        });
    }

    if (customers.length) {
        activity.push({
            title: `${customers.length} customers`,
            meta: "Customer management"
        });
    }

    if (employees.length) {
        activity.push({
            title: `${employees.length} employees`,
            meta: "Team"
        });
    }

    if (!activity.length) {
        activity.push({
            title: "No activity recorded yet",
            meta: "Start using your business modules"
        });
    }

    $("activityList").innerHTML = activity
        .map(item => `
            <div class="activity">
                <strong>${escapeHtml(item.title)}</strong>
                <span class="muted">${escapeHtml(item.meta)}</span>
            </div>
        `)
        .join("");

    const lowStock = products.filter(product => {
        const quantity = Number(product.quantity ?? 0);
        const reorder = Number(product.reorder_level ?? 0);
        return quantity <= reorder;
    });

    if (!lowStock.length) {
        $("stockList").innerHTML = `
            <div class="activity">
                <strong>Stock looks healthy</strong>
                <span class="muted">No products currently below reorder level.</span>
            </div>
        `;
    } else {
        $("stockList").innerHTML = lowStock
            .slice(0, 8)
            .map(product => `
                <div class="activity">
                    <strong>${escapeHtml(product.name || "Unnamed product")}</strong>
                    <span class="muted">
                        Stock: ${Number(product.quantity ?? 0)}
                        / Reorder: ${Number(product.reorder_level ?? 0)}
                    </span>
                </div>
            `)
            .join("");
    }

    $("connectionStatus").textContent = "Connected to IMRAN BUSINESS OS API";
}

    } finally {
        dashboardLoading = false;
    }

function showCustomerForm(customer = null) {
    const existing = document.getElementById("customerModal");

    if (existing) {
        existing.remove();
    }

    const editing = Boolean(customer);

    const modal = document.createElement("div");
    modal.id = "customerModal";
    modal.className = "modal-backdrop";

    modal.innerHTML = `
        <div class="modal-card">
            <div class="modal-header">
                <div>
                    <span class="eyebrow">CUSTOMER MANAGEMENT</span>
                    <h3>${editing ? "Edit customer" : "New customer"}</h3>
                </div>
                <button type="button" class="modal-close" id="customerModalClose">×</button>
            </div>

            <form id="customerForm">
                <label>
                    Name
                    <input id="customerName" type="text"
                        value="${escapeHtml(customer?.name || "")}"
                        required>
                </label>

                <label>
                    Phone
                    <input id="customerPhone" type="text"
                        value="${escapeHtml(customer?.phone || "")}">
                </label>

                <label>
                    Email
                    <input id="customerEmail" type="email"
                        value="${escapeHtml(customer?.email || "")}">
                </label>

                <label>
                    Address
                    <textarea id="customerAddress" rows="3">${escapeHtml(customer?.address || "")}</textarea>
                </label>

                <div id="customerFormError" class="error"></div>

                <div class="modal-actions">
                    <button type="button" class="secondary-button" id="customerCancel">
                        Cancel
                    </button>
                    <button type="submit">
                        ${editing ? "Save changes" : "Create customer"}
                    </button>
                </div>
            </form>
        </div>
    `;

    document.body.appendChild(modal);

    const close = () => modal.remove();

    document.getElementById("customerModalClose")
        .addEventListener("click", close);

    document.getElementById("customerCancel")
        .addEventListener("click", close);

    modal.addEventListener("click", event => {
        if (event.target === modal) {
            close();
        }
    });

    document.getElementById("customerForm")
        .addEventListener("submit", async event => {
            event.preventDefault();

            const errorBox = document.getElementById("customerFormError");
            errorBox.textContent = "";

            const payload = {
                name: document.getElementById("customerName").value.trim(),
                phone: document.getElementById("customerPhone").value.trim() || null,
                email: document.getElementById("customerEmail").value.trim() || null,
                address: document.getElementById("customerAddress").value.trim() || null
            };

            if (!payload.name) {
                errorBox.textContent = "Customer name is required.";
                return;
            }

            try {
                if (editing) {
                    await api(`/api/v1/customers/${customer.id}`, {
                        method: "PATCH",
                        body: JSON.stringify(payload)
                    });
                } else {
                    await api("/api/v1/customers", {
                        method: "POST",
                        body: JSON.stringify(payload)
                    });
                }

                close();
                await loadSection("customers");

            } catch (error) {
                errorBox.textContent = error.message;
            }
        });
}

async function loadCustomers() {
    $("dashboard").classList.add("hidden");
    $("genericSection").classList.remove("hidden");

    $("pageTitle").textContent = "Customers";
    $("sectionHeading").innerHTML = `
        <div class="section-title-row">
            <span>Customers</span>
            <button id="newCustomerButton" class="small-button">
                + New customer
            </button>
        </div>
    `;

    $("records").textContent = "Loading...";
    $("recordCount").textContent = "";

    try {
        const data = await api("/api/v1/customers");
        const records = extractRecords(data);

        $("recordCount").textContent =
            `${records.length} customer${records.length === 1 ? "" : "s"}`;

        document.getElementById("newCustomerButton")
            .addEventListener("click", () => showCustomerForm());

        if (!records.length) {
            $("records").innerHTML = `
                <div class="empty-state">
                    <strong>No customers yet</strong>
                    <span>Create your first customer directly inside IMRAN BUSINESS OS.</span>
                </div>
            `;
            return;
        }

        $("records").innerHTML = records
            .slice(0, 100)
            .map(customer => `
                <div class="record customer-record">
                    <div class="record-main">
                        <div class="record-title">
                            ${escapeHtml(customer.name || "Unnamed customer")}
                        </div>

                        <div class="record-meta">
                            ${customer.phone ? `Phone: ${escapeHtml(customer.phone)}` : ""}
                            ${customer.email ? ` • Email: ${escapeHtml(customer.email)}` : ""}
                            ${customer.address ? ` • Address: ${escapeHtml(customer.address)}` : ""}
                        </div>
                    </div>

                    <div class="record-actions">
                        <button
                            class="small-button edit-customer"
                            data-id="${escapeHtml(customer.id)}">
                            Edit
                        </button>

                        <button
                            class="small-button danger-button delete-customer"
                            data-id="${escapeHtml(customer.id)}">
                            Delete
                        </button>
                    </div>
                </div>
            `)
            .join("");

        document.querySelectorAll(".edit-customer")
            .forEach(button => {
                button.addEventListener("click", () => {
                    const customer = records.find(
                        item => item.id === button.dataset.id
                    );

                    if (customer) {
                        showCustomerForm(customer);
                    }
                });
            });

        document.querySelectorAll(".delete-customer")
            .forEach(button => {
                button.addEventListener("click", async () => {
                    const customer = records.find(
                        item => item.id === button.dataset.id
                    );

                    if (!customer) return;

                    if (!confirm(
                        `Delete customer "${customer.name}"?`
                    )) {
                        return;
                    }

                    try {
                        await api(`/api/v1/customers/${customer.id}`, {
                            method: "DELETE"
                        });

                        await loadCustomers();

                    } catch (error) {
                        $("globalError").textContent = error.message;
                    }
                });
            });

    } catch (error) {
        $("records").innerHTML = `
            <div class="record">
                <div class="record-title">Unable to load customers</div>
                <div class="record-meta">
                    ${escapeHtml(error.message)}
                </div>
            </div>
        `;
    }
}

async function loadSection(section) {
    if (section === "dashboard") {
        $("dashboard").classList.remove("hidden");
        $("genericSection").classList.add("hidden");
        $("pageTitle").textContent = "Dashboard";
        await loadDashboard();
        return;
    }

    if (section === "customers") {
        await loadCustomers();
        return;
    }

    const config = sections[section];

    if (!config) return;

    $("dashboard").classList.add("hidden");
    $("genericSection").classList.remove("hidden");

    $("pageTitle").textContent = config.title;
    $("sectionHeading").textContent = config.title;
    $("records").textContent = "Loading...";

    try {
        const data = await api(config.endpoint);
        const records = extractRecords(data);

        $("recordCount").textContent = `${records.length} records`;

        if (!records.length) {
            $("records").innerHTML = `
                <div class="record">
                    <div class="record-title">No records</div>
                    <div class="record-meta">
                        Nothing has been recorded in this module yet.
                    </div>
                </div>
            `;
            return;
        }

        $("records").innerHTML = records
            .slice(0, 100)
            .map(record => {
                const title =
                    record.name ||
                    record.title ||
                    record.full_name ||
                    record.invoice_number ||
                    record.quotation_number ||
                    record.job_number ||
                    record.id ||
                    "Record";

                const meta = Object.entries(record)
                    .filter(([key]) =>
                        !["id", "business_id", "created_at"].includes(key)
                    )
                    .slice(0, 5)
                    .map(([key, value]) =>
                        `${key}: ${value ?? ""}`
                    )
                    .join(" • ");

                return `
                    <div class="record">
                        <div class="record-title">
                            ${escapeHtml(String(title))}
                        </div>
                        <div class="record-meta">
                            ${escapeHtml(meta)}
                        </div>
                    </div>
                `;
            })
            .join("");

    } catch (error) {
        $("records").innerHTML = `
            <div class="record">
                <div class="record-title">Unable to load records</div>
                <div class="record-meta">
                    ${escapeHtml(error.message)}
                </div>
            </div>
        `;
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

$("loginForm").addEventListener("submit", async event => {
    event.preventDefault();

    $("loginError").textContent = "";

    try {
        await login(
            $("email").value.trim(),
            $("password").value
        );

        $("loginScreen").classList.add("hidden");
        $("appScreen").classList.remove("hidden");

        await loadDashboard();
    } catch (error) {
        $("loginError").textContent = error.message;
    }
});

$("logoutButton").addEventListener("click", logout);

$("refreshButton").addEventListener("click", async () => {
    try {
        await loadSection(currentSection);
    } catch (error) {
        $("globalError").textContent = error.message;
    }
});

document.querySelectorAll(".nav-item").forEach(button => {
    button.addEventListener("click", async () => {
        document.querySelectorAll(".nav-item")
            .forEach(item => item.classList.remove("active"));

        button.classList.add("active");
        currentSection = button.dataset.section;

        await loadSection(currentSection);
    });
});

async function initialize() {
    if (!token) {
        $("loginScreen").classList.remove("hidden");
        $("appScreen").classList.add("hidden");
        return;
    }

    $("loginScreen").classList.add("hidden");
    $("appScreen").classList.remove("hidden");
    $("connectionStatus").textContent = "Loading...";

    try {
        const me = await api("/api/v1/auth/me");

        const business = me?.business || {};
        const user = me?.user || {};

        $("businessName").textContent =
            business.name || "IMRAN BUSINESS OS";

        $("businessInfo").textContent =
            [
                business.category,
                business.country_code,
                business.currency_code
            ]
            .filter(Boolean)
            .join(" • ");

        $("userInfo").textContent =
            [
                user.email,
                user.role
            ]
            .filter(Boolean)
            .join(" • ");

        $("connectionStatus").textContent = "Connected";

        await loadDashboard();

    } catch (error) {
        console.error("Startup error:", error);

        token = null;
        localStorage.removeItem("imran_access_token");

        $("appScreen").classList.add("hidden");
        $("loginScreen").classList.remove("hidden");

        $("loginError").textContent =
            error.message || "Unable to load business.";
    }
}

initialize();
