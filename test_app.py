import os
import io
import pytest
from app import create_app
from models import db, Account, Income, StudentLoan, Transaction, Budget, convert_to_usd, get_eur_to_usd_rate

@pytest.fixture
def test_client():
    test_db = os.path.abspath("test_finances.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{test_db}"
    })

    with app.test_client() as client:
        with app.app_context():
            yield client

    if os.path.exists(test_db):
        os.remove(test_db)


def test_home_page(test_client):
    res = test_client.get("/")
    assert res.status_code == 200
    assert b"Odysseus Finance" in res.data
    assert b"Student Loans Tracker" in res.data


def test_conversion_math():
    # USD stays USD
    assert convert_to_usd(100.0, "USD", 1.08) == 100.0
    # EUR converts at rate
    assert round(convert_to_usd(100.0, "EUR", 1.08), 2) == 108.0
    assert round(convert_to_usd(50.0, "EUR", 1.10), 2) == 55.0


def test_summary_api(test_client):
    res = test_client.get("/api/summary")
    assert res.status_code == 200
    data = res.get_json()
    assert "net_worth_usd" in data
    assert "total_balance_usd" in data
    assert "total_loan_balance_usd" in data
    assert "monthly_income_usd" in data
    assert data["currency"] == "USD"
    assert data["eur_to_usd_rate"] == 1.08
    assert data["accounts_count"] >= 3
    assert data["loans_count"] >= 2


def test_accounts_api(test_client):
    # GET
    res = test_client.get("/api/accounts")
    assert res.status_code == 200
    accounts = res.get_json()
    assert len(accounts) >= 3

    # POST new account
    new_acc = {
        "name": "French Livret Developpement Durable",
        "type": "savings",
        "currency": "EUR",
        "balance": 3000.0
    }
    res_post = test_client.post("/api/accounts", json=new_acc)
    assert res_post.status_code == 201
    created = res_post.get_json()
    assert created["name"] == "French Livret Developpement Durable"
    assert created["balance"] == 3000.0
    # EUR converted to USD: 3000 * 1.08 = 3240.0
    assert created["balance_usd"] == 3240.0


def test_loans_api(test_client):
    # GET
    res = test_client.get("/api/loans")
    assert res.status_code == 200
    loans = res.get_json()
    assert len(loans) >= 2

    # POST new loan
    new_loan = {
        "lender": "Discover Student Loan",
        "principal": 10000.0,
        "balance": 8500.0,
        "interest_rate": 6.2,
        "monthly_payment": 120.0,
        "next_due_date": "2026-11-20",
        "status": "active",
        "currency": "USD"
    }
    res_post = test_client.post("/api/loans", json=new_loan)
    assert res_post.status_code == 201
    data = res_post.get_json()
    assert data["lender"] == "Discover Student Loan"
    assert data["balance_usd"] == 8500.0


def test_transactions_crud(test_client):
    # POST transaction
    payload = {
        "description": "Trader Joe Market Run",
        "amount": 75.50,
        "is_expense": True,
        "currency": "USD",
        "category": "Groceries",
        "date": "2026-10-30"
    }
    res = test_client.post("/api/transactions", json=payload)
    assert res.status_code == 201
    tx_data = res.get_json()
    tx_id = tx_data["id"]
    assert tx_data["amount"] == -75.50

    # GET with filter
    res_filter = test_client.get("/api/transactions?category=Groceries")
    assert res_filter.status_code == 200
    items = res_filter.get_json()
    assert any(i["id"] == tx_id for i in items)

    # DELETE
    res_del = test_client.delete(f"/api/transactions/{tx_id}")
    assert res_del.status_code == 200
    assert res_del.get_json()["success"] is True


def test_settings_fx_update(test_client):
    # PUT update EUR to USD rate
    res = test_client.put("/api/settings", json={"eur_to_usd_rate": 1.15})
    assert res.status_code == 200
    data = res.get_json()
    assert data["eur_to_usd_rate"] == 1.15

    # Check that summary accounts reflect the new rate
    sum_res = test_client.get("/api/summary")
    sum_data = sum_res.get_json()
    assert sum_data["eur_to_usd_rate"] == 1.15


def test_csv_import(test_client):
    csv_content = """Date,Description,Amount
2026-10-25,Whole Foods Market,-45.20
2026-10-26,Uber Transit Trip,-22.50
2026-10-27,Client Deposit Bonus,500.00
"""
    data = {
        "file": (io.BytesIO(csv_content.encode("utf-8")), "bank_statement.csv"),
        "currency": "USD"
    }
    res = test_client.post("/api/import-csv", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    summary = res.get_json()
    assert summary["imported"] == 3
    assert summary["skipped"] == 0
