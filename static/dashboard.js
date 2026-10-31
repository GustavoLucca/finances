// Personal Finance Dashboard - Vanilla JS Frontend

let currentAccounts = [];

function formatUSD(num) {
    if (num === null || num === undefined) return "$0.00";
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 2
    }).format(num);
}

function formatNative(num, currency) {
    if (num === null || num === undefined) return "0.00";
    const curr = (currency || "USD").toUpperCase();
    if (curr === "EUR") {
        return new Intl.NumberFormat("de-DE", {
            style: "currency",
            currency: "EUR"
        }).format(num);
    }
    return formatUSD(num);
}

// --- Fetch & Render Summary ---
async function loadSummary() {
    try {
        const res = await fetch("/api/summary");
        const data = await res.json();

        document.getElementById("kpiNetWorth").textContent = formatUSD(data.net_worth_usd);
        document.getElementById("kpiAssets").textContent = formatUSD(data.total_balance_usd);
        document.getElementById("kpiLoans").textContent = formatUSD(data.total_loan_balance_usd);
        document.getElementById("kpiLoanPayment").textContent = formatUSD(data.monthly_loan_payments_usd);
        document.getElementById("kpiIncome").textContent = formatUSD(data.monthly_income_usd);
        document.getElementById("kpiExpenses").textContent = formatUSD(data.monthly_expenses_usd);
        document.getElementById("kpiAccountCount").textContent = data.accounts_count;

        document.getElementById("navFxRate").textContent = Number(data.eur_to_usd_rate).toFixed(4);
        document.getElementById("settingEurToUsd").value = Number(data.eur_to_usd_rate).toFixed(4);
    } catch (err) {
        console.error("Error loading summary:", err);
    }
}

// --- Fetch & Render Accounts ---
async function loadAccounts() {
    try {
        const res = await fetch("/api/accounts");
        currentAccounts = await res.json();

        // Update tables
        const tbody = document.querySelector("#accountsTable tbody");
        if (currentAccounts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No accounts added yet.</td></tr>';
        } else {
            tbody.innerHTML = currentAccounts.map(a => `
                <tr>
                    <td><strong>${a.name}</strong></td>
                    <td><span class="badge ${a.type === 'savings' ? 'bg-info text-dark' : 'bg-secondary'}">${a.type}</span></td>
                    <td><code>${formatNative(a.balance, a.currency)}</code></td>
                    <td><strong class="text-primary">${formatUSD(a.balance_usd)}</strong></td>
                </tr>
            `).join("");
        }

        // Update account selects in modals
        const txSelect = document.getElementById("txAccountSelect");
        const csvSelect = document.getElementById("csvAccountSelect");

        const optionsHtml = currentAccounts.map(a => `<option value="${a.id}">${a.name} (${a.currency})</option>`).join("");
        txSelect.innerHTML = '<option value="">Unassigned</option>' + optionsHtml;
        csvSelect.innerHTML = '<option value="">-- Generic / None --</option>' + optionsHtml;

    } catch (err) {
        console.error("Error loading accounts:", err);
    }
}

// --- Fetch & Render Income ---
async function loadIncome() {
    try {
        const res = await fetch("/api/income");
        const items = await res.json();
        const tbody = document.querySelector("#incomeTable tbody");

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No income streams added.</td></tr>';
        } else {
            tbody.innerHTML = items.map(i => `
                <tr>
                    <td><strong>${i.source}</strong></td>
                    <td><span class="badge bg-light text-dark border">${i.frequency}</span></td>
                    <td><code>${formatNative(i.amount, i.currency)}</code></td>
                    <td><strong class="text-income">${formatUSD(i.monthly_usd)}</strong>/mo</td>
                </tr>
            `).join("");
        }
    } catch (err) {
        console.error("Error loading income:", err);
    }
}

// --- Fetch & Render Student Loans ---
async function loadLoans() {
    try {
        const res = await fetch("/api/loans");
        const loans = await res.json();
        const tbody = document.querySelector("#loansTable tbody");

        if (loans.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-3">No student loans recorded.</td></tr>';
        } else {
            tbody.innerHTML = loans.map(l => `
                <tr>
                    <td><strong>${l.lender}</strong></td>
                    <td><strong class="text-danger">${formatUSD(l.balance_usd)}</strong></td>
                    <td><span class="text-muted small">${formatUSD(l.principal_usd)}</span></td>
                    <td>${l.interest_rate}%</td>
                    <td>${formatUSD(l.monthly_payment_usd)}/mo</td>
                    <td>${l.next_due_date || '-'}</td>
                    <td>
                        <span class="badge ${l.status === 'active' ? 'bg-warning text-dark' : (l.status === 'paid_off' ? 'bg-success' : 'bg-secondary')}">
                            ${l.status}
                        </span>
                    </td>
                </tr>
            `).join("");
        }
    } catch (err) {
        console.error("Error loading loans:", err);
    }
}

// --- Fetch & Render Budgets ---
async function loadBudgets() {
    try {
        const res = await fetch("/api/budgets");
        const budgets = await res.json();
        const container = document.getElementById("budgetsContainer");

        if (budgets.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-3">No budget limits defined yet.</div>';
            return;
        }

        container.innerHTML = budgets.map(b => {
            let barColor = "bg-success";
            if (b.percent_used > 100) barColor = "bg-danger";
            else if (b.percent_used > 80) barColor = "bg-warning";

            return `
                <div class="mb-3">
                    <div class="d-flex justify-content-between align-items-center small mb-1">
                        <strong>${b.category}</strong>
                        <span>
                            <strong class="${b.remaining_usd < 0 ? 'text-danger' : 'text-dark'}">${formatUSD(b.spent_usd)}</strong>
                            / ${formatUSD(b.monthly_limit_usd)}
                            <span class="text-muted">(${b.percent_used}%)</span>
                        </span>
                    </div>
                    <div class="progress progress-thin">
                        <div class="progress-bar ${barColor}" style="width: ${Math.min(b.percent_used, 100)}%;"></div>
                    </div>
                </div>
            `;
        }).join("");
    } catch (err) {
        console.error("Error loading budgets:", err);
    }
}

// --- Fetch & Render Transactions ---
async function loadTransactions() {
    try {
        const category = document.getElementById("txCategoryFilter").value;
        const search = document.getElementById("txSearchInput").value.trim();

        let url = `/api/transactions?limit=50`;
        if (category && category !== "All") url += `&category=${encodeURIComponent(category)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        const res = await fetch(url);
        const txs = await res.json();
        const tbody = document.getElementById("txTableBody");

        if (txs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No transactions found.</td></tr>';
            return;
        }

        tbody.innerHTML = txs.map(t => {
            const isDeposit = t.amount > 0;
            const sign = isDeposit ? "+" : "-";
            const amtClass = isDeposit ? "text-income" : "text-expense";

            return `
                <tr>
                    <td class="text-muted small">${t.date || '-'}</td>
                    <td>
                        <strong>${t.description}</strong>
                        ${t.import_source === 'csv' ? '<span class="badge bg-light text-secondary border ms-1" style="font-size:0.65rem;">CSV</span>' : ''}
                    </td>
                    <td><span class="badge bg-light text-dark border">${t.category}</span></td>
                    <td class="small text-muted">${t.account_name || 'Unassigned'}</td>
                    <td><code>${sign}${formatNative(Math.abs(t.amount), t.currency)}</code></td>
                    <td><strong class="${amtClass}">${sign}${formatUSD(Math.abs(t.amount_usd))}</strong></td>
                    <td>
                        <button class="btn btn-sm btn-outline-danger py-0 px-2 btn-delete-tx" data-id="${t.id}" title="Delete transaction">
                            &times;
                        </button>
                    </td>
                </tr>
            `;
        }).join("");

        // Attach delete events
        document.querySelectorAll(".btn-delete-tx").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                const id = e.currentTarget.getAttribute("data-id");
                if (confirm("Delete this transaction?")) {
                    await fetch(`/api/transactions/${id}`, { method: "DELETE" });
                    refreshAll();
                }
            });
        });

    } catch (err) {
        console.error("Error loading transactions:", err);
    }
}

// --- Render Plotly Charts ---
async function loadCharts() {
    try {
        // 1. Spending by Category (Donut Chart)
        const pieRes = await fetch("/api/charts/spending-by-category?days=30");
        const pieData = await pieRes.json();

        if (pieData.labels && pieData.labels.length > 0) {
            Plotly.newPlot("chartSpendingPie", [{
                values: pieData.values,
                labels: pieData.labels,
                type: "pie",
                hole: 0.55,
                textinfo: "label+percent",
                marker: {
                    colors: [
                        "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
                        "#ec4899", "#06b6d4", "#64748b", "#14b8a6"
                    ]
                }
            }], {
                margin: { t: 10, b: 20, l: 10, r: 10 },
                showlegend: false
            }, { responsive: true, displayModeBar: false });
        } else {
            document.getElementById("chartSpendingPie").innerHTML = '<div class="text-center text-muted py-5">No expense data available for pie chart.</div>';
        }

        // 2. Cash Flow Trend (Grouped Bar Chart)
        const flowRes = await fetch("/api/charts/monthly-trend");
        const flowData = await flowRes.json();

        if (flowData.months && flowData.months.length > 0) {
            Plotly.newPlot("chartCashFlow", [
                {
                    x: flowData.months,
                    y: flowData.income,
                    name: "Income",
                    type: "bar",
                    marker: { color: "#16a34a" }
                },
                {
                    x: flowData.months,
                    y: flowData.expenses,
                    name: "Expenses",
                    type: "bar",
                    marker: { color: "#dc2626" }
                }
            ], {
                barmode: "group",
                margin: { t: 20, b: 35, l: 50, r: 20 },
                legend: { orientation: "h", y: 1.15, x: 0.5, xanchor: "center" },
                yaxis: { tickprefix: "$" }
            }, { responsive: true, displayModeBar: false });
        }

        // 3. Student Loans Progress (Stacked Bar Chart)
        const loanRes = await fetch("/api/charts/loan-progress");
        const loanData = await loanRes.json();

        if (loanData.lenders && loanData.lenders.length > 0) {
            Plotly.newPlot("chartLoanProgress", [
                {
                    y: loanData.lenders,
                    x: loanData.paid_off,
                    name: "Paid Off",
                    type: "bar",
                    orientation: "h",
                    marker: { color: "#22c55e" }
                },
                {
                    y: loanData.lenders,
                    x: loanData.balances,
                    name: "Remaining Balance",
                    type: "bar",
                    orientation: "h",
                    marker: { color: "#ef4444" }
                }
            ], {
                barmode: "stack",
                margin: { t: 10, b: 25, l: 140, r: 20 },
                legend: { orientation: "h", y: 1.25, x: 0.5, xanchor: "center" },
                xaxis: { tickprefix: "$" }
            }, { responsive: true, displayModeBar: false });
        } else {
            document.getElementById("chartLoanProgress").innerHTML = '<div class="text-center text-muted py-3">No loan data available.</div>';
        }

    } catch (err) {
        console.error("Error loading charts:", err);
    }
}

// --- Refresh Everything ---
async function refreshAll() {
    await Promise.all([
        loadSummary(),
        loadAccounts(),
        loadIncome(),
        loadLoans(),
        loadBudgets(),
        loadTransactions(),
        loadCharts()
    ]);
}

// --- Form Listeners & Modals Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    // Initial load
    refreshAll();

    // Auto-fill today's date in add transaction form
    document.getElementById("txDate").value = new Date().toISOString().split("T")[0];

    // Filter listeners
    document.getElementById("txCategoryFilter").addEventListener("change", loadTransactions);
    let searchDebounce;
    document.getElementById("txSearchInput").addEventListener("input", () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(loadTransactions, 250);
    });

    // Form: Add Transaction
    const formAddTx = document.getElementById("formAddTransaction");
    formAddTx.addEventListener("submit", async (e) => {
        e.preventDefault();
        const isExpense = document.querySelector('input[name="txType"]:checked').value === "expense";
        const payload = {
            description: document.getElementById("txDesc").value.trim(),
            amount: parseFloat(document.getElementById("txAmount").value),
            currency: document.getElementById("txCurrency").value,
            category: document.getElementById("txCategory").value,
            date: document.getElementById("txDate").value,
            account_id: document.getElementById("txAccountSelect").value || null,
            is_expense: isExpense
        };

        const res = await fetch("/api/transactions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById("addTransactionModal")).hide();
            formAddTx.reset();
            document.getElementById("txDate").value = new Date().toISOString().split("T")[0];
            refreshAll();
        } else {
            const err = await res.json();
            alert("Error: " + (err.error || "Failed to add transaction"));
        }
    });

    // Form: Import CSV
    const formImportCsv = document.getElementById("formImportCsv");
    formImportCsv.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById("csvFileInput");
        if (!fileInput.files || fileInput.files.length === 0) return;

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        formData.append("account_id", document.getElementById("csvAccountSelect").value);
        formData.append("currency", document.getElementById("csvCurrencySelect").value);

        const btn = document.getElementById("btnDoImport");
        btn.disabled = true;
        btn.textContent = "Importing...";

        const alertBox = document.getElementById("importResultAlert");
        alertBox.className = "alert d-none";

        try {
            const res = await fetch("/api/import-csv", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (res.ok) {
                alertBox.className = "alert alert-success mt-3 py-2 small";
                alertBox.innerHTML = `✅ Successfully imported <strong>${data.imported}</strong> transactions (${data.skipped} skipped).`;
                refreshAll();
                setTimeout(() => {
                    bootstrap.Modal.getInstance(document.getElementById("importCsvModal")).hide();
                    formImportCsv.reset();
                    alertBox.className = "alert d-none";
                }, 1800);
            } else {
                alertBox.className = "alert alert-danger mt-3 py-2 small";
                alertBox.textContent = "Error: " + (data.error || "Failed to parse CSV");
            }
        } catch (err) {
            alertBox.className = "alert alert-danger mt-3 py-2 small";
            alertBox.textContent = "Upload failed: " + err.message;
        } finally {
            btn.disabled = false;
            btn.textContent = "Parse & Import";
        }
    });

    // Form: Add Account
    const formAddAccount = document.getElementById("formAddAccount");
    formAddAccount.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById("accName").value.trim(),
            type: document.getElementById("accType").value,
            currency: document.getElementById("accCurrency").value,
            balance: parseFloat(document.getElementById("accBalance").value)
        };

        const res = await fetch("/api/accounts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById("addAccountModal")).hide();
            formAddAccount.reset();
            refreshAll();
        } else {
            const err = await res.json();
            alert("Error: " + (err.error || "Failed to add account"));
        }
    });

    // Form: Add Loan
    const formAddLoan = document.getElementById("formAddLoan");
    formAddLoan.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            lender: document.getElementById("loanLender").value.trim(),
            principal: parseFloat(document.getElementById("loanPrincipal").value),
            balance: parseFloat(document.getElementById("loanBalance").value),
            interest_rate: parseFloat(document.getElementById("loanRate").value),
            monthly_payment: parseFloat(document.getElementById("loanPayment").value || 0),
            next_due_date: document.getElementById("loanDueDate").value || null,
            status: document.getElementById("loanStatus").value
        };

        const res = await fetch("/api/loans", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById("addLoanModal")).hide();
            formAddLoan.reset();
            refreshAll();
        } else {
            const err = await res.json();
            alert("Error: " + (err.error || "Failed to add loan"));
        }
    });

    // Form: Add Income
    const formAddIncome = document.getElementById("formAddIncome");
    formAddIncome.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            source: document.getElementById("incSource").value.trim(),
            amount: parseFloat(document.getElementById("incAmount").value),
            currency: document.getElementById("incCurrency").value,
            frequency: document.getElementById("incFrequency").value
        };

        const res = await fetch("/api/income", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById("addIncomeModal")).hide();
            formAddIncome.reset();
            refreshAll();
        } else {
            const err = await res.json();
            alert("Error: " + (err.error || "Failed to add income"));
        }
    });

    // Form: Set Budget
    const formSetBudget = document.getElementById("formSetBudget");
    formSetBudget.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            category: document.getElementById("budgetCategory").value,
            monthly_limit_usd: parseFloat(document.getElementById("budgetLimit").value)
        };

        const res = await fetch("/api/budgets", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById("setBudgetModal")).hide();
            formSetBudget.reset();
            refreshAll();
        } else {
            const err = await res.json();
            alert("Error: " + (err.error || "Failed to set budget"));
        }
    });

    // Form: Settings FX
    const formSettings = document.getElementById("formSettings");
    formSettings.addEventListener("submit", async (e) => {
        e.preventDefault();
        const rate = parseFloat(document.getElementById("settingEurToUsd").value);
        const res = await fetch("/api/settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ eur_to_usd_rate: rate })
        });

        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById("settingsModal")).hide();
            refreshAll();
        } else {
            const err = await res.json();
            alert("Error: " + (err.error || "Failed to update FX rate"));
        }
    });
});
