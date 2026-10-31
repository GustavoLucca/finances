import io
import re
from datetime import datetime, date
import pandas as pd
from models import db, Transaction, Account

# Keyword heuristics for automatic categorization
CATEGORY_KEYWORDS = {
    "Groceries": [
        "grocery", "market", "trader joe", "whole foods", "safeway", "kroger", "costco",
        "carrefour", "aldi", "lidl", "supermarket", "monoprix", "food lion", "wegmans"
    ],
    "Housing": [
        "rent", "mortgage", "landlord", "lease", "property", "hoa", "apartment"
    ],
    "Utilities": [
        "electric", "power", "water", "sewer", "gas bill", "internet", "wifi", "broadband",
        "verizon", "at&t", "t-mobile", "comcast", "xfinity", "edf", "engie", "energy"
    ],
    "Transport": [
        "uber", "lyft", "taxi", "cab", "metro", "subway", "transit", "bus", "train",
        "amtrak", "sncf", "shell", "chevron", "bp", "exxon", "gas station", "parking", "toll"
    ],
    "Entertainment": [
        "netflix", "spotify", "hulu", "disney", "apple music", "steam", "nintendo", "playstation",
        "cinema", "theater", "concert", "restaurant", "cafe", "coffee", "starbucks", "bar", "pub", "bistro"
    ],
    "Healthcare": [
        "pharmacy", "cvs", "walgreens", "doctor", "clinic", "hospital", "dentist", "dental",
        "health", "medical", "optometry", "vision", "prescription"
    ],
    "Education": [
        "tuition", "university", "college", "school", "student loan", "nelnet", "aidvantage",
        "sallie mae", "mohela", "books", "course", "udemy", "coursera"
    ],
    "Income": [
        "payroll", "direct dep", "salary", "wages", "bonus", "dividend", "interest payment", "deposit"
    ]
}


def guess_category(description: str, amount: float) -> str:
    desc_lower = (description or "").lower()
    if amount > 0 and any(k in desc_lower for k in CATEGORY_KEYWORDS["Income"]):
        return "Income"
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if cat == "Income" and amount < 0:
            continue
        for kw in keywords:
            if kw in desc_lower:
                return cat
    return "Income" if amount > 0 else "Other"


def parse_clean_amount(val) -> float:
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    is_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_negative = True
        val_str = val_str[1:-1]
    if val_str.startswith("-"):
        is_negative = True
        val_str = val_str[1:]
    # Remove currency symbols and formatting spaces
    val_str = re.sub(r"[^\d.,]", "", val_str)
    if not val_str:
        return 0.0

    # Handle European decimal formatting (e.g. 1.250,50 vs 1,250.50)
    if "," in val_str and "." in val_str:
        if val_str.rfind(",") > val_str.rfind("."):
            # 1.250,50 -> 1250.50
            val_str = val_str.replace(".", "").replace(",", ".")
        else:
            # 1,250.50 -> 1250.50
            val_str = val_str.replace(",", "")
    elif "," in val_str and "." not in val_str:
        # Check if comma is decimal (e.g., 25,50) or thousand (e.g., 1,000)
        parts = val_str.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            val_str = val_str.replace(",", ".")
        else:
            val_str = val_str.replace(",", "")

    try:
        amount = float(val_str)
        return -amount if is_negative else amount
    except ValueError:
        return 0.0


def parse_clean_date(val) -> date:
    if pd.isna(val) or not val:
        return date.today()
    if isinstance(val, (datetime, date)):
        return val if isinstance(val, date) else val.date()
    val_str = str(val).strip()
    # Try common bank date formats
    for fmt in (
        "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y",
        "%Y/%m/%d", "%b %d, %Y", "%d %b %Y", "%d %B %Y", "%Y%m%d"
    ):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    # Fallback with pandas to_datetime
    try:
        dt = pd.to_datetime(val_str)
        return dt.date()
    except Exception:
        return date.today()


def find_column(columns, candidates):
    cols_clean = {re.sub(r"[_\s\W]+", "", str(c).lower()): c for c in columns}
    for cand in candidates:
        cand_clean = re.sub(r"[_\s\W]+", "", cand.lower())
        if cand_clean in cols_clean:
            return cols_clean[cand_clean]
    # Substring match fallback
    for cand in candidates:
        for clean_col, orig_col in cols_clean.items():
            if cand in clean_col:
                return orig_col
    return None


def parse_csv_data(file_stream_or_path, default_account_id=None, default_currency=None):
    """
    Parses a CSV file from a path or file-like object and creates Transaction objects.
    """
    # Detect delimiter and encoding
    if isinstance(file_stream_or_path, (str, bytes)):
        if isinstance(file_stream_or_path, str) and not file_stream_or_path.endswith(".csv") and "\n" in file_stream_or_path:
            buffer = io.StringIO(file_stream_or_path)
            df = pd.read_csv(buffer, sep=None, engine="python")
        else:
            df = pd.read_csv(file_stream_or_path, sep=None, engine="python")
    else:
        # File storage object from Flask
        content = file_stream_or_path.read()
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        buffer = io.StringIO(text)
        df = pd.read_csv(buffer, sep=None, engine="python")

    # Clean columns
    df.columns = [str(c).strip() for c in df.columns]

    date_col = find_column(df.columns, ["date", "transactiondate", "posteddate", "datum", "fecha"])
    desc_col = find_column(df.columns, ["description", "memo", "details", "narrative", "payee", "name", "libelle"])
    amount_col = find_column(df.columns, ["amount", "montant", "betrag", "importe", "value"])
    debit_col = find_column(df.columns, ["debit", "withdrawal", "spent", "debitamount", "out"])
    credit_col = find_column(df.columns, ["credit", "deposit", "in", "creditamount"])
    cat_col = find_column(df.columns, ["category", "type"])
    curr_col = find_column(df.columns, ["currency", "devise"])

    if not date_col and not desc_col and not (amount_col or debit_col):
        raise ValueError("Could not detect standard bank statement columns (date, description, amount).")

    # Look up account details if provided
    account = None
    if default_account_id:
        account = db.session.get(Account, default_account_id)
    fallback_curr = default_currency or (account.currency if account else "USD")

    imported = 0
    skipped = 0
    errors = []
    created_txs = []

    for idx, row in df.iterrows():
        try:
            # Parse Date
            tx_date = parse_clean_date(row[date_col]) if date_col and pd.notna(row[date_col]) else date.today()

            # Parse Description
            tx_desc = str(row[desc_col]).strip() if desc_col and pd.notna(row[desc_col]) else "Imported transaction"
            if not tx_desc or tx_desc.lower() == "nan":
                tx_desc = "Imported transaction"

            # Parse Amount
            if amount_col and pd.notna(row[amount_col]):
                amount = parse_clean_amount(row[amount_col])
            elif debit_col or credit_col:
                debit = parse_clean_amount(row[debit_col]) if debit_col and pd.notna(row[debit_col]) else 0.0
                credit = parse_clean_amount(row[credit_col]) if credit_col and pd.notna(row[credit_col]) else 0.0
                # Debit is negative (outflow), credit is positive (inflow)
                amount = credit - abs(debit)
            else:
                skipped += 1
                continue

            if abs(amount) < 0.0001:
                skipped += 1
                continue

            # Parse Currency
            if curr_col and pd.notna(row[curr_col]):
                curr = str(row[curr_col]).upper().strip()
                if curr not in ("USD", "EUR"):
                    curr = fallback_curr
            else:
                curr = fallback_curr

            # Parse or Guess Category
            if cat_col and pd.notna(row[cat_col]) and str(row[cat_col]).strip().lower() != "nan":
                cat = str(row[cat_col]).strip().title()
            else:
                cat = guess_category(tx_desc, amount)

            tx = Transaction(
                account_id=default_account_id,
                date=tx_date,
                description=tx_desc,
                category=cat,
                amount=amount,
                currency=curr,
                import_source="csv"
            )
            db.session.add(tx)
            created_txs.append(tx)
            imported += 1
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")
            skipped += 1

    # Update account balance if account is specified
    if account and created_txs:
        sum_delta = sum(t.amount for t in created_txs)
        account.balance += sum_delta

    db.session.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:5],
        "total_rows": len(df)
    }
