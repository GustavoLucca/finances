# Odysseus Finance Dashboard

A local, 100% offline personal finance dashboard for tracking and budgeting across accounts, income streams, expenses, and student loans with multi-currency support (USD + EUR converted to USD).

---

## Quick Start

1. Open your terminal and navigate to the project directory:
   ```bash
   cd /Users/gustavolucca/odysseus/finances
   ```

2. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

3. Launch the dashboard:
   ```bash
   python app.py
   ```

4. Open your browser at:
   **[http://127.0.0.1:5050](http://127.0.0.1:5050)**

---

## Features

- **Consolidated Financial Baseline:**
  - **Net Worth**: Total Liquid Assets (Checking + Savings) minus Total Student Loans.
  - **Liquid Balances**: Live sum of checking and savings accounts in USD (converting EUR balances automatically).
  - **Student Loans Tracker**: Dedicated tracking of lenders, current balance, original principal, interest rate %, monthly payment, and next due date.
  - **Monthly Inflow & Outflow**: Automated calculations of expected monthly income and 30-day category expenses.

- **Offline Multi-Currency Handling:**
  - Stores each account and transaction in its native currency (`USD` or `EUR`).
  - Converts all totals, charts, and budget comparisons to **USD** using an exchange rate stored in SQLite (default: `1 EUR = 1.0800 USD`).
  - Click the **💱 Exchange Rate pill** or **⚙️ Settings** to update the FX rate anytime.

- **Interactive Local Visualizations (Plotly.js):**
  - **Donut Chart**: 30-Day spending breakdown by category.
  - **Grouped Bar Chart**: Cash flow trends comparing income vs expenses.
  - **Paydown Progress Chart**: Horizontal stacked bar chart showing paid-off vs remaining principal per student loan.

- **Bank CSV Importer:**
  - Import bank export CSVs directly into any account without sensitive cloud credentials.
  - Automatic column recognition (`Date`, `Description`, `Amount` / `Debit` / `Credit`).
  - Built-in categorization heuristics (Groceries, Housing, Transport, Utilities, Entertainment, Healthcare, Education, Income).

- **Automated Tests:**
  ```bash
  pytest test_app.py -v
  ```
