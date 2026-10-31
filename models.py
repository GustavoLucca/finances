from datetime import datetime, date, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {"key": self.key, "value": self.value}


class Account(db.Model):
    __tablename__ = "accounts"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(50), nullable=False, default="checking")  # checking, savings
    currency = db.Column(db.String(3), nullable=False, default="USD")   # USD, EUR
    balance = db.Column(db.Float, nullable=False, default=0.0)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    transactions = db.relationship("Transaction", backref="account", lazy=True, cascade="all, delete-orphan")

    def to_dict(self, eur_to_usd=None):
        if eur_to_usd is None:
            eur_to_usd = get_eur_to_usd_rate()
        usd_balance = convert_to_usd(self.balance, self.currency, eur_to_usd)
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "currency": self.currency,
            "balance": round(self.balance, 2),
            "balance_usd": round(usd_balance, 2),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Income(db.Model):
    __tablename__ = "income"
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    frequency = db.Column(db.String(50), nullable=False, default="monthly")  # monthly, biweekly, one-time
    effective_date = db.Column(db.Date, nullable=True, default=date.today)

    def monthly_equivalent_usd(self, eur_to_usd=None):
        usd_amount = convert_to_usd(self.amount, self.currency, eur_to_usd)
        freq = (self.frequency or "monthly").lower()
        if freq == "biweekly":
            return usd_amount * 26.0 / 12.0
        elif freq == "weekly":
            return usd_amount * 52.0 / 12.0
        elif freq == "annual":
            return usd_amount / 12.0
        return usd_amount

    def to_dict(self, eur_to_usd=None):
        if eur_to_usd is None:
            eur_to_usd = get_eur_to_usd_rate()
        usd_amount = convert_to_usd(self.amount, self.currency, eur_to_usd)
        return {
            "id": self.id,
            "source": self.source,
            "amount": round(self.amount, 2),
            "currency": self.currency,
            "amount_usd": round(usd_amount, 2),
            "frequency": self.frequency,
            "monthly_usd": round(self.monthly_equivalent_usd(eur_to_usd), 2),
            "effective_date": self.effective_date.isoformat() if self.effective_date else None
        }


class Transaction(db.Model):
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="Other")
    amount = db.Column(db.Float, nullable=False)  # positive = deposit/credit, negative = expense/debit
    currency = db.Column(db.String(3), nullable=False, default="USD")
    import_source = db.Column(db.String(50), nullable=False, default="manual")  # manual, csv
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self, eur_to_usd=None):
        if eur_to_usd is None:
            eur_to_usd = get_eur_to_usd_rate()
        usd_amount = convert_to_usd(self.amount, self.currency, eur_to_usd)
        return {
            "id": self.id,
            "account_id": self.account_id,
            "account_name": self.account.name if self.account else "Unassigned",
            "date": self.date.isoformat() if self.date else None,
            "description": self.description,
            "category": self.category,
            "amount": round(self.amount, 2),
            "currency": self.currency,
            "amount_usd": round(usd_amount, 2),
            "import_source": self.import_source
        }


class StudentLoan(db.Model):
    __tablename__ = "student_loans"
    id = db.Column(db.Integer, primary_key=True)
    lender = db.Column(db.String(120), nullable=False)
    principal = db.Column(db.Float, nullable=False)
    balance = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False, default=5.0)  # annual percentage
    monthly_payment = db.Column(db.Float, nullable=False, default=0.0)
    next_due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), nullable=False, default="active")  # active, deferred, paid_off
    currency = db.Column(db.String(3), nullable=False, default="USD")

    def to_dict(self, eur_to_usd=None):
        if eur_to_usd is None:
            eur_to_usd = get_eur_to_usd_rate()
        usd_balance = convert_to_usd(self.balance, self.currency, eur_to_usd)
        usd_principal = convert_to_usd(self.principal, self.currency, eur_to_usd)
        usd_payment = convert_to_usd(self.monthly_payment, self.currency, eur_to_usd)
        return {
            "id": self.id,
            "lender": self.lender,
            "principal": round(self.principal, 2),
            "principal_usd": round(usd_principal, 2),
            "balance": round(self.balance, 2),
            "balance_usd": round(usd_balance, 2),
            "interest_rate": round(self.interest_rate, 2),
            "monthly_payment": round(self.monthly_payment, 2),
            "monthly_payment_usd": round(usd_payment, 2),
            "next_due_date": self.next_due_date.isoformat() if self.next_due_date else None,
            "status": self.status,
            "currency": self.currency
        }


class Budget(db.Model):
    __tablename__ = "budgets"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), unique=True, nullable=False)
    monthly_limit_usd = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "monthly_limit_usd": round(self.monthly_limit_usd, 2)
        }


def get_setting(key, default=None):
    s = Setting.query.filter_by(key=key).first()
    return s.value if s else default


def set_setting(key, value):
    s = Setting.query.filter_by(key=key).first()
    if s:
        s.value = str(value)
    else:
        s = Setting(key=key, value=str(value))
        db.session.add(s)
    db.session.commit()
    return s.value


def get_eur_to_usd_rate():
    try:
        val = get_setting("eur_to_usd_rate", "1.08")
        return float(val)
    except Exception:
        return 1.08


def convert_to_usd(amount, currency, eur_to_usd=None):
    if amount is None:
        return 0.0
    if eur_to_usd is None:
        eur_to_usd = get_eur_to_usd_rate()
    curr = (currency or "USD").upper().strip()
    if curr == "EUR":
        return amount * eur_to_usd
    return float(amount)
