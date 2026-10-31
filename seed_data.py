from datetime import date, timedelta
from models import db, Setting, Account, Income, Transaction, StudentLoan, Budget, set_setting

def seed_database():
    # Only seed if tables are empty
    if Account.query.first():
        print("Database already contains data, skipping seed.")
        return

    print("Seeding initial financial baseline data...")

    # 1. Settings
    set_setting("eur_to_usd_rate", "1.08")
    set_setting("dashboard_currency", "USD")

    # 2. Accounts
    chase = Account(
        name="Chase Total Checking",
        type="checking",
        currency="USD",
        balance=4850.50
    )
    vanguard = Account(
        name="Vanguard Cash Reserves (HYSA)",
        type="savings",
        currency="USD",
        balance=18400.00
    )
    bnp = Account(
        name="BNP Paribas Livret A",
        type="savings",
        currency="EUR",
        balance=6250.00  # ~ $6,750 USD
    )
    db.session.add_all([chase, vanguard, bnp])
    db.session.flush()

    # 3. Income Sources
    salary = Income(
        source="Senior Software Engineer Salary",
        amount=6250.00,
        currency="USD",
        frequency="monthly",
        effective_date=date.today() - timedelta(days=90)
    )
    freelance = Income(
        source="EU Consulting Retainer",
        amount=1200.00,
        currency="EUR",
        frequency="monthly",
        effective_date=date.today() - timedelta(days=60)
    )
    interest = Income(
        source="HYSA Interest Yield",
        amount=82.50,
        currency="USD",
        frequency="monthly",
        effective_date=date.today() - timedelta(days=90)
    )
    db.session.add_all([salary, freelance, interest])

    # 4. Student Loans (Student loans only, per confirmed spec)
    loan1 = StudentLoan(
        lender="Aidvantage Direct Subsidized (Undergrad)",
        principal=16000.00,
        balance=11420.00,
        interest_rate=4.53,
        monthly_payment=175.00,
        next_due_date=date.today() + timedelta(days=12),
        status="active",
        currency="USD"
    )
    loan2 = StudentLoan(
        lender="Mohela Direct Unsubsidized (Graduate)",
        principal=28500.00,
        balance=23850.00,
        interest_rate=5.28,
        monthly_payment=310.00,
        next_due_date=date.today() + timedelta(days=19),
        status="active",
        currency="USD"
    )
    db.session.add_all([loan1, loan2])

    # 5. Budgets
    budgets = [
        Budget(category="Housing", monthly_limit_usd=1850.00),
        Budget(category="Groceries", monthly_limit_usd=650.00),
        Budget(category="Transport", monthly_limit_usd=250.00),
        Budget(category="Utilities", monthly_limit_usd=220.00),
        Budget(category="Entertainment", monthly_limit_usd=350.00),
        Budget(category="Healthcare", monthly_limit_usd=120.00),
        Budget(category="Education", monthly_limit_usd=485.00),
        Budget(category="Other", monthly_limit_usd=200.00)
    ]
    db.session.add_all(budgets)

    # 6. Sample Transactions (Last 45 days)
    today = date.today()
    sample_txs = [
        # Incomes
        (today - timedelta(days=1), "Tech Corp Monthly Direct Deposit", "Income", 6250.00, "USD", chase.id),
        (today - timedelta(days=5), "Client Paris Consulting Wire", "Income", 1200.00, "EUR", bnp.id),
        (today - timedelta(days=28), "Vanguard Monthly Interest Payment", "Income", 82.50, "USD", vanguard.id),
        (today - timedelta(days=31), "Tech Corp Monthly Direct Deposit", "Income", 6250.00, "USD", chase.id),
        (today - timedelta(days=35), "Client Paris Consulting Wire", "Income", 1200.00, "EUR", bnp.id),

        # Housing & Utilities
        (today - timedelta(days=2), "Monthly Apartment Rent Payment", "Housing", -1750.00, "USD", chase.id),
        (today - timedelta(days=6), "ConEd Electric & Gas Utility", "Utilities", -118.40, "USD", chase.id),
        (today - timedelta(days=9), "Gigabit Fiber Internet", "Utilities", -79.99, "USD", chase.id),
        (today - timedelta(days=32), "Monthly Apartment Rent Payment", "Housing", -1750.00, "USD", chase.id),
        (today - timedelta(days=36), "ConEd Electric & Gas Utility", "Utilities", -124.15, "USD", chase.id),

        # Student Loans Payments
        (today - timedelta(days=14), "Aidvantage Student Loan Auto-Debit", "Education", -175.00, "USD", chase.id),
        (today - timedelta(days=20), "Mohela Loan Servicing Auto-Debit", "Education", -310.00, "USD", chase.id),
        (today - timedelta(days=44), "Aidvantage Student Loan Auto-Debit", "Education", -175.00, "USD", chase.id),

        # Groceries (USD and EUR)
        (today - timedelta(days=3), "Trader Joe's Weekly Groceries", "Groceries", -112.45, "USD", chase.id),
        (today - timedelta(days=7), "Whole Foods Market", "Groceries", -84.30, "USD", chase.id),
        (today - timedelta(days=11), "Carrefour Supermarché Paris", "Groceries", -68.50, "EUR", bnp.id),
        (today - timedelta(days=15), "Costco Wholesale Bulk Run", "Groceries", -185.20, "USD", chase.id),
        (today - timedelta(days=22), "Trader Joe's Weekly Groceries", "Groceries", -96.10, "USD", chase.id),
        (today - timedelta(days=34), "Monoprix Gourmet", "Groceries", -54.20, "EUR", bnp.id),

        # Transport
        (today - timedelta(days=4), "MTA Subway Monthly MetroCard", "Transport", -132.00, "USD", chase.id),
        (today - timedelta(days=8), "Uber Ride Home Airport", "Transport", -42.80, "USD", chase.id),
        (today - timedelta(days=16), "RATP Paris Metro Carnet", "Transport", -21.50, "EUR", bnp.id),
        (today - timedelta(days=25), "Lyft Airport Transit", "Transport", -36.40, "USD", chase.id),

        # Entertainment & Dining
        (today - timedelta(days=3), "Spotify Family Subscription", "Entertainment", -16.99, "USD", chase.id),
        (today - timedelta(days=5), "Netflix Premium 4K", "Entertainment", -22.99, "USD", chase.id),
        (today - timedelta(days=10), "Dinner at Le Comptoir Bistro", "Entertainment", -85.00, "EUR", bnp.id),
        (today - timedelta(days=13), "Steam Video Game Store", "Entertainment", -49.99, "USD", chase.id),
        (today - timedelta(days=18), "Blue Bottle Coffee Roasters", "Entertainment", -18.75, "USD", chase.id),
        (today - timedelta(days=27), "Concert Tickets Ticketmaster", "Entertainment", -140.00, "USD", chase.id),

        # Healthcare & Other
        (today - timedelta(days=12), "CVS Pharmacy Prescription", "Healthcare", -34.50, "USD", chase.id),
        (today - timedelta(days=24), "Dental Copay Cleaning", "Healthcare", -45.00, "USD", chase.id),
        (today - timedelta(days=17), "Amazon Home Essentials", "Other", -64.20, "USD", chase.id),
        (today - timedelta(days=29), "Patagonia Gear Repair", "Other", -48.00, "USD", chase.id)
    ]

    for dt, desc, cat, amt, curr, acct_id in sample_txs:
        tx = Transaction(
            account_id=acct_id,
            date=dt,
            description=desc,
            category=cat,
            amount=amt,
            currency=curr,
            import_source="sample"
        )
        db.session.add(tx)

    db.session.commit()
    print("Database seeding completed successfully.")
