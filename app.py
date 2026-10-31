import os
from datetime import date, timedelta
from flask import Flask, render_template, request, jsonify
from models import db, Setting, Account, Income, Transaction, StudentLoan, Budget, \
                   get_setting, set_setting, get_eur_to_usd_rate, convert_to_usd
from csv_import import parse_csv_data
from seed_data import seed_database

def create_app(test_config=None):
    app = Flask(__name__, static_folder="static", template_folder="templates")

    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, "finances.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_database()

    # --- HTML View ---
    @app.route("/")
    def index():
        return render_template("dashboard.html")

    # --- Summary API ---
    @app.route("/api/summary", methods=["GET"])
    def get_summary():
        eur_to_usd = get_eur_to_usd_rate()
        
        # 1. Accounts Total Balance (Net Liquid Assets)
        accounts = Account.query.all()
        total_balance_usd = sum(convert_to_usd(a.balance, a.currency, eur_to_usd) for a in accounts)

        # 2. Total Monthly Income
        incomes = Income.query.all()
        monthly_income_usd = sum(inc.monthly_equivalent_usd(eur_to_usd) for inc in incomes)

        # 3. Monthly Expenses (last 30 days)
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_txs = Transaction.query.filter(Transaction.date >= thirty_days_ago).all()
        monthly_expenses_usd = sum(
            abs(convert_to_usd(t.amount, t.currency, eur_to_usd))
            for t in recent_txs if t.amount < 0
        )

        # 4. Student Loans
        loans = StudentLoan.query.all()
        total_loan_balance_usd = sum(convert_to_usd(l.balance, l.currency, eur_to_usd) for l in loans)
        monthly_loan_payments_usd = sum(
            convert_to_usd(l.monthly_payment, l.currency, eur_to_usd)
            for l in loans if l.status == "active"
        )

        # 5. Net Worth = Total Liquid Assets - Student Loans
        net_worth_usd = total_balance_usd - total_loan_balance_usd

        return jsonify({
            "currency": "USD",
            "eur_to_usd_rate": eur_to_usd,
            "total_balance_usd": round(total_balance_usd, 2),
            "monthly_income_usd": round(monthly_income_usd, 2),
            "monthly_expenses_usd": round(monthly_expenses_usd, 2),
            "total_loan_balance_usd": round(total_loan_balance_usd, 2),
            "monthly_loan_payments_usd": round(monthly_loan_payments_usd, 2),
            "net_worth_usd": round(net_worth_usd, 2),
            "accounts_count": len(accounts),
            "loans_count": len(loans)
        })

    # --- Accounts API ---
    @app.route("/api/accounts", methods=["GET", "POST"])
    def handle_accounts():
        eur_to_usd = get_eur_to_usd_rate()
        if request.method == "POST":
            data = request.json or {}
            name = data.get("name", "").strip()
            if not name:
                return jsonify({"error": "Account name is required"}), 400
            
            acc = Account(
                name=name,
                type=data.get("type", "checking"),
                currency=data.get("currency", "USD").upper(),
                balance=float(data.get("balance", 0.0))
            )
            db.session.add(acc)
            db.session.commit()
            return jsonify(acc.to_dict(eur_to_usd)), 201

        accounts = Account.query.order_by(Account.name).all()
        return jsonify([a.to_dict(eur_to_usd) for a in accounts])

    # --- Income API ---
    @app.route("/api/income", methods=["GET", "POST"])
    def handle_income():
        eur_to_usd = get_eur_to_usd_rate()
        if request.method == "POST":
            data = request.json or {}
            source = data.get("source", "").strip()
            if not source:
                return jsonify({"error": "Income source name is required"}), 400
            
            inc = Income(
                source=source,
                amount=float(data.get("amount", 0.0)),
                currency=data.get("currency", "USD").upper(),
                frequency=data.get("frequency", "monthly")
            )
            db.session.add(inc)
            db.session.commit()
            return jsonify(inc.to_dict(eur_to_usd)), 201

        incomes = Income.query.all()
        return jsonify([i.to_dict(eur_to_usd) for i in incomes])

    # --- Student Loans API ---
    @app.route("/api/loans", methods=["GET", "POST"])
    def handle_loans():
        eur_to_usd = get_eur_to_usd_rate()
        if request.method == "POST":
            data = request.json or {}
            lender = data.get("lender", "").strip()
            if not lender:
                return jsonify({"error": "Lender name is required"}), 400
            
            due_str = data.get("next_due_date")
            due_date = date.fromisoformat(due_str) if due_str else None

            loan = StudentLoan(
                lender=lender,
                principal=float(data.get("principal", 0.0)),
                balance=float(data.get("balance", 0.0)),
                interest_rate=float(data.get("interest_rate", 5.0)),
                monthly_payment=float(data.get("monthly_payment", 0.0)),
                next_due_date=due_date,
                status=data.get("status", "active"),
                currency=data.get("currency", "USD").upper()
            )
            db.session.add(loan)
            db.session.commit()
            return jsonify(loan.to_dict(eur_to_usd)), 201

        loans = StudentLoan.query.all()
        return jsonify([l.to_dict(eur_to_usd) for l in loans])

    # --- Transactions API ---
    @app.route("/api/transactions", methods=["GET", "POST"])
    def handle_transactions():
        eur_to_usd = get_eur_to_usd_rate()
        if request.method == "POST":
            data = request.json or {}
            desc = data.get("description", "").strip()
            if not desc:
                return jsonify({"error": "Description is required"}), 400

            amt = float(data.get("amount", 0.0))
            is_expense = data.get("is_expense", True)
            if is_expense and amt > 0:
                amt = -amt

            tx_date = date.fromisoformat(data.get("date")) if data.get("date") else date.today()
            account_id = data.get("account_id")
            if account_id:
                try:
                    account_id = int(account_id)
                except ValueError:
                    account_id = None

            currency = data.get("currency", "USD").upper()
            if account_id:
                acc = db.session.get(Account, account_id)
                if acc:
                    currency = acc.currency
                    acc.balance += amt

            tx = Transaction(
                account_id=account_id,
                date=tx_date,
                description=desc,
                category=data.get("category", "Other"),
                amount=amt,
                currency=currency,
                import_source="manual"
            )
            db.session.add(tx)
            db.session.commit()
            return jsonify(tx.to_dict(eur_to_usd)), 201

        # Query with filtering
        query = Transaction.query
        category = request.args.get("category")
        if category and category != "All":
            query = query.filter_by(category=category)
        
        account_id = request.args.get("account_id")
        if account_id:
            query = query.filter_by(account_id=int(account_id))

        search = request.args.get("search")
        if search:
            query = query.filter(Transaction.description.ilike(f"%{search}%"))

        query = query.order_by(Transaction.date.desc(), Transaction.id.desc())
        
        limit = int(request.args.get("limit", 50))
        txs = query.limit(limit).all()
        return jsonify([t.to_dict(eur_to_usd) for t in txs])

    @app.route("/api/transactions/<int:tx_id>", methods=["DELETE"])
    def delete_transaction(tx_id):
        tx = db.session.get(Transaction, tx_id)
        if not tx:
            return jsonify({"error": "Transaction not found"}), 404
        if tx.account_id:
            acc = db.session.get(Account, tx.account_id)
            if acc:
                acc.balance -= tx.amount
        db.session.delete(tx)
        db.session.commit()
        return jsonify({"success": True, "id": tx_id})

    # --- Budgets API ---
    @app.route("/api/budgets", methods=["GET", "POST"])
    def handle_budgets():
        eur_to_usd = get_eur_to_usd_rate()
        if request.method == "POST":
            data = request.json or {}
            category = data.get("category", "").strip()
            limit_usd = float(data.get("monthly_limit_usd", 0.0))
            if not category:
                return jsonify({"error": "Category is required"}), 400

            b = Budget.query.filter_by(category=category).first()
            if b:
                b.monthly_limit_usd = limit_usd
            else:
                b = Budget(category=category, monthly_limit_usd=limit_usd)
                db.session.add(b)
            db.session.commit()
            return jsonify(b.to_dict()), 200

        budgets = Budget.query.all()
        # Compute spent in last 30 days per category
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_expenses = Transaction.query.filter(
            Transaction.date >= thirty_days_ago,
            Transaction.amount < 0
        ).all()

        spending_by_cat = {}
        for tx in recent_expenses:
            usd = abs(convert_to_usd(tx.amount, tx.currency, eur_to_usd))
            spending_by_cat[tx.category] = spending_by_cat.get(tx.category, 0.0) + usd

        result = []
        for b in budgets:
            spent = round(spending_by_cat.get(b.category, 0.0), 2)
            pct = round((spent / b.monthly_limit_usd * 100) if b.monthly_limit_usd > 0 else 0, 1)
            result.append({
                "id": b.id,
                "category": b.category,
                "monthly_limit_usd": round(b.monthly_limit_usd, 2),
                "spent_usd": spent,
                "remaining_usd": round(b.monthly_limit_usd - spent, 2),
                "percent_used": pct
            })
        return jsonify(result)

    # --- Settings API ---
    @app.route("/api/settings", methods=["GET", "PUT"])
    def handle_settings():
        if request.method == "PUT":
            data = request.json or {}
            if "eur_to_usd_rate" in data:
                try:
                    rate = float(data["eur_to_usd_rate"])
                    if rate <= 0:
                        return jsonify({"error": "Exchange rate must be positive"}), 400
                    set_setting("eur_to_usd_rate", str(rate))
                except ValueError:
                    return jsonify({"error": "Invalid exchange rate number"}), 400
            return jsonify({
                "eur_to_usd_rate": get_eur_to_usd_rate(),
                "dashboard_currency": get_setting("dashboard_currency", "USD")
            })

        return jsonify({
            "eur_to_usd_rate": get_eur_to_usd_rate(),
            "dashboard_currency": get_setting("dashboard_currency", "USD")
        })

    # --- CSV Import API ---
    @app.route("/api/import-csv", methods=["POST"])
    def import_csv():
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Empty filename"}), 400

        account_id = request.form.get("account_id")
        account_id = int(account_id) if account_id and account_id != "" else None
        currency = request.form.get("currency")

        try:
            summary = parse_csv_data(file, default_account_id=account_id, default_currency=currency)
            return jsonify(summary), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    # --- Charts API ---
    @app.route("/api/charts/spending-by-category", methods=["GET"])
    def chart_spending_by_category():
        eur_to_usd = get_eur_to_usd_rate()
        days = int(request.args.get("days", 30))
        since_date = date.today() - timedelta(days=days)

        txs = Transaction.query.filter(
            Transaction.date >= since_date,
            Transaction.amount < 0
        ).all()

        breakdown = {}
        for tx in txs:
            usd_amt = abs(convert_to_usd(tx.amount, tx.currency, eur_to_usd))
            cat = tx.category or "Other"
            breakdown[cat] = breakdown.get(cat, 0.0) + usd_amt

        labels = sorted(breakdown.keys(), key=lambda k: breakdown[k], reverse=True)
        values = [round(breakdown[k], 2) for k in labels]
        return jsonify({"labels": labels, "values": values})

    @app.route("/api/charts/monthly-trend", methods=["GET"])
    def chart_monthly_trend():
        eur_to_usd = get_eur_to_usd_rate()
        
        # Aggregate past 6 months
        months_data = {}
        today = date.today()
        for i in range(5, -1, -1):
            # approximate month keys
            ref_date = today - timedelta(days=i * 30)
            key = ref_date.strftime("%Y-%m")
            months_data[key] = {"income": 0.0, "expenses": 0.0}

        txs = Transaction.query.all()
        for tx in txs:
            month_key = tx.date.strftime("%Y-%m")
            if month_key in months_data:
                usd = convert_to_usd(tx.amount, tx.currency, eur_to_usd)
                if usd > 0:
                    months_data[month_key]["income"] += usd
                else:
                    months_data[month_key]["expenses"] += abs(usd)

        # Also add fixed regular income for months that have records
        incomes = Income.query.all()
        monthly_base_income = sum(inc.monthly_equivalent_usd(eur_to_usd) for inc in incomes)

        labels = list(months_data.keys())
        income_vals = []
        expense_vals = []
        for m in labels:
            inc = months_data[m]["income"]
            # If transaction deposit already recorded, keep max or recorded
            final_inc = max(inc, monthly_base_income)
            income_vals.append(round(final_inc, 2))
            expense_vals.append(round(months_data[m]["expenses"], 2))

        return jsonify({
            "months": labels,
            "income": income_vals,
            "expenses": expense_vals
        })

    @app.route("/api/charts/loan-progress", methods=["GET"])
    def chart_loan_progress():
        eur_to_usd = get_eur_to_usd_rate()
        loans = StudentLoan.query.all()
        
        lenders = []
        balances = []
        paid_offs = []
        for l in loans:
            lenders.append(l.lender.split(" (")[0]) # Cleaner short name
            bal_usd = convert_to_usd(l.balance, l.currency, eur_to_usd)
            prin_usd = convert_to_usd(l.principal, l.currency, eur_to_usd)
            paid_usd = max(0.0, prin_usd - bal_usd)
            balances.append(round(bal_usd, 2))
            paid_offs.append(round(paid_usd, 2))

        return jsonify({
            "lenders": lenders,
            "balances": balances,
            "paid_off": paid_offs
        })

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5050))
    print(f"🚀 Starting Finance Dashboard at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
