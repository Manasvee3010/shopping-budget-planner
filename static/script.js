let expenses = [];
let expenseChart = null;
let currentBudget = 0;

document.addEventListener("DOMContentLoaded", function () {
    setTodayDate();
    loadTheme();
    loadBudget();
    loadExpenses();
});

function setTodayDate() {
    const dateInput = document.getElementById("date");

    if (dateInput) {
        const today = new Date().toISOString().split("T")[0];
        dateInput.value = today;
    }
}

async function loadBudget() {
    try {
        const response = await fetch("/api/budget");

        if (!response.ok) {
            throw new Error("Unable to load budget");
        }

        const data = await response.json();

        currentBudget = Number(data.amount) || 0;

        document.getElementById("totalBudget").textContent =
            formatCurrency(currentBudget);

        document.getElementById("budgetInput").value =
            currentBudget;

        updateSummary();
    } catch (error) {
        console.error("Budget loading error:", error);
    }
}

document.getElementById("budgetBtn").addEventListener("click", async function () {
    const input = document.getElementById("budgetInput");
    const amount = parseFloat(input.value);

    if (isNaN(amount) || amount < 0) {
        alert("Please enter a valid budget.");
        return;
    }

    try {
        const response = await fetch("/api/budget", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                amount: amount
            })
        });

        const data = await response.json();

        if (!data.success) {
            alert(data.message);
            return;
        }

        currentBudget = amount;

        document.getElementById("totalBudget").textContent =
            formatCurrency(currentBudget);

        updateSummary();

        alert("Budget updated successfully!");
    } catch (error) {
        console.error("Budget update error:", error);
        alert("Unable to update budget.");
    }
});

async function loadExpenses() {
    try {
        const response = await fetch("/api/expenses");

        if (!response.ok) {
            throw new Error("Unable to load expenses");
        }

        expenses = await response.json();

        displayExpenses(expenses);
        updateSummary();
        updateChart();
    } catch (error) {
        console.error("Expense loading error:", error);

        document.getElementById("expenseTableBody").innerHTML = `
            <tr>
                <td colspan="6" style="text-align:center; padding:30px;">
                    Unable to load expenses.
                </td>
            </tr>
        `;
    }
}

document.getElementById("expenseForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    const item = document.getElementById("item").value.trim();
    const category = document.getElementById("category").value;
    const amount = parseFloat(document.getElementById("amount").value);
    const date = document.getElementById("date").value;

    if (!item || !category || isNaN(amount) || amount <= 0 || !date) {
        alert("Please enter all details correctly.");
        return;
    }

    try {
        const response = await fetch("/api/expenses", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                item: item,
                category: category,
                amount: amount,
                date: date
            })
        });

        const data = await response.json();

        if (!data.success) {
            alert(data.message);
            return;
        }

        document.getElementById("expenseForm").reset();

        setTodayDate();

        await loadExpenses();
    } catch (error) {
        console.error("Add expense error:", error);
        alert("Unable to add expense.");
    }
});

function displayExpenses(data) {
    const tableBody = document.getElementById("expenseTableBody");

    tableBody.innerHTML = "";

    if (data.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align:center; padding:30px; color:var(--muted);">
                    No expenses found.
                </td>
            </tr>
        `;

        return;
    }

    data.forEach(function (expense, index) {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${index + 1}</td>

            <td>
                <strong>${escapeHTML(expense.item)}</strong>
            </td>

            <td>
                <span class="category-badge">
                    ${escapeHTML(expense.category)}
                </span>
            </td>

            <td>
                <strong>
                    ${formatCurrency(expense.amount)}
                </strong>
            </td>

            <td>
                ${formatDate(expense.date)}
            </td>

            <td>
                <button
                    class="delete-btn"
                    onclick="deleteExpense(${expense.id})"
                >
                    Delete
                </button>
            </td>
        `;

        tableBody.appendChild(row);
    });
}

async function deleteExpense(id) {
    const confirmed = confirm(
        "Are you sure you want to delete this expense?"
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(
            "/api/expenses/" + id,
            {
                method: "DELETE"
            }
        );

        const data = await response.json();

        if (!data.success) {
            alert(data.message);
            return;
        }

        await loadExpenses();
    } catch (error) {
        console.error("Delete error:", error);
        alert("Unable to delete expense.");
    }
}

document.getElementById("clearBtn").addEventListener("click", async function () {
    if (expenses.length === 0) {
        alert("There is no data to clear.");
        return;
    }

    const confirmed = confirm(
        "This will permanently delete ALL shopping expenses. Continue?"
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(
            "/api/expenses",
            {
                method: "DELETE"
            }
        );

        const data = await response.json();

        if (!data.success) {
            alert(data.message);
            return;
        }

        await loadExpenses();

        alert("All expense data has been cleared.");
    } catch (error) {
        console.error("Clear data error:", error);
        alert("Unable to clear data.");
    }
});

function updateSummary() {
    const totalSpent = expenses.reduce(function (total, expense) {
        return total + Number(expense.amount);
    }, 0);

    const remaining = currentBudget - totalSpent;

    document.getElementById("totalBudget").textContent =
        formatCurrency(currentBudget);

    document.getElementById("totalSpent").textContent =
        formatCurrency(totalSpent);

    document.getElementById("remaining").textContent =
        formatCurrency(remaining);

    document.getElementById("totalItems").textContent =
        expenses.length;

    const remainingElement = document.getElementById("remaining");

    if (remaining < 0) {
        remainingElement.style.color = "#ef4444";
    } else {
        remainingElement.style.color = "#10b981";
    }

    updateBudgetNotification(totalSpent);
}

function updateBudgetNotification(totalSpent) {
    const notification = document.getElementById("budgetNotification");
    const title = document.getElementById("notificationTitle");
    const message = document.getElementById("notificationMessage");
    const icon = document.getElementById("notificationIcon");

    if (!notification || !title || !message || !icon) {
        return;
    }

    notification.classList.remove("hidden");

    if (currentBudget <= 0) {
        icon.textContent = "💰";
        title.textContent = "Set Your Budget";
        message.textContent =
            "Set a shopping budget to start tracking your spending.";
        return;
    }

    const percentage = (totalSpent / currentBudget) * 100;

    if (totalSpent > currentBudget) {
        icon.textContent = "🚨";
        title.textContent = "Budget Exceeded!";
        message.textContent =
            "You have exceeded your shopping budget.";
    } else if (percentage >= 80) {
        icon.textContent = "⚠️";
        title.textContent = "You Are Close to Your Budget Limit";
        message.textContent =
            "You have used " +
            percentage.toFixed(0) +
            "% of your budget.";
    } else {
        icon.textContent = "✅";
        title.textContent = "You Are Within Your Budget";
        message.textContent =
            "Your spending is currently within your planned budget.";
    }
}

function updateChart() {
    const categoryTotals = {};

    expenses.forEach(function (expense) {
        const category = expense.category;
        const amount = Number(expense.amount);

        if (!categoryTotals[category]) {
            categoryTotals[category] = 0;
        }

        categoryTotals[category] += amount;
    });

    const labels = Object.keys(categoryTotals);
    const values = Object.values(categoryTotals);

    const canvas = document.getElementById("expenseChart");

    if (!canvas) {
        return;
    }

    if (expenseChart) {
        expenseChart.destroy();
    }

    if (labels.length === 0) {
        return;
    }

    expenseChart = new Chart(canvas, {
        type: "doughnut",

        data: {
            labels: labels,

            datasets: [
                {
                    label: "Shopping Expenses",
                    data: values,
                    borderWidth: 2
                }
            ]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    position: "bottom"
                },

                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return (
                                context.label +
                                ": " +
                                formatCurrency(context.raw)
                            );
                        }
                    }
                }
            }
        }
    });
}

document.getElementById("searchInput").addEventListener(
    "input",
    filterExpenses
);

document.getElementById("filterCategory").addEventListener(
    "change",
    filterExpenses
);

function filterExpenses() {
    const search = document
        .getElementById("searchInput")
        .value
        .toLowerCase()
        .trim();

    const category =
        document.getElementById("filterCategory").value;

    const filtered = expenses.filter(function (expense) {
        const itemName = String(expense.item).toLowerCase();

        const matchesSearch =
            itemName.includes(search);

        const matchesCategory =
            category === "All" ||
            expense.category === category;

        return matchesSearch && matchesCategory;
    });

    displayExpenses(filtered);
}

document.getElementById("themeBtn").addEventListener(
    "click",
    function () {
        document.body.classList.toggle("dark");

        const isDark =
            document.body.classList.contains("dark");

        if (isDark) {
            document.getElementById("themeBtn").textContent =
                "☀️ Light Mode";

            localStorage.setItem("theme", "dark");
        } else {
            document.getElementById("themeBtn").textContent =
                "🌙 Dark Mode";

            localStorage.setItem("theme", "light");
        }
    }
);

function loadTheme() {
    const theme = localStorage.getItem("theme");

    if (theme === "dark") {
        document.body.classList.add("dark");

        document.getElementById("themeBtn").textContent =
            "☀️ Light Mode";
    }
}

function formatCurrency(amount) {
    return (
        "₹" +
        Number(amount).toLocaleString("en-IN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })
    );
}

function formatDate(dateString) {
    const date = new Date(dateString + "T00:00:00");

    return date.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}

function escapeHTML(text) {
    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}