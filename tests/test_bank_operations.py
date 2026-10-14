from decimal import Decimal

import mysql.connector
import pytest

import account
import customer
import queries
import transaction
from database import BankError, execute, db_transaction, fetch_all, fetch_one


# ---------- helpers ----------

def new_customer(name="Asha Rao", email="asha@example.com", phone="9876543210"):
    return customer.add_customer(name, email, phone)


@pytest.fixture
def two_accounts():
    cid = new_customer()
    first = account.create_account(cid, "SAVINGS", "1000")
    second = account.create_account(cid, "CURRENT", "500")
    return first["account_number"], second["account_number"]


def balance(number):
    return account.get_balance(number)


def count_rows(table):
    return fetch_one(f"SELECT COUNT(*) AS n FROM {table}")["n"]


# ---------- customers ----------

def test_add_valid_customer():
    cid = new_customer()
    assert customer.get_customer(cid)["name"] == "Asha Rao"


@pytest.mark.parametrize("name,email,phone", [
    ("", "a@example.com", "9876543210"),
    ("Asha", "", "9876543210"),
    ("Asha", "a@example.com", ""),
    ("   ", "a@example.com", "9876543210"),
])
def test_reject_empty_fields(name, email, phone):
    with pytest.raises(BankError):
        customer.add_customer(name, email, phone)


def test_reject_bad_email_and_phone():
    with pytest.raises(BankError):
        customer.add_customer("Asha", "not-an-email", "9876543210")
    with pytest.raises(BankError):
        customer.add_customer("Asha", "a@example.com", "12ab")


def test_reject_duplicate_email_and_phone():
    new_customer()
    with pytest.raises(BankError, match="email"):
        customer.add_customer("Other", "asha@example.com", "9000000001")
    with pytest.raises(BankError, match="phone"):
        customer.add_customer("Other", "other@example.com", "9876543210")


def test_search_customer():
    new_customer()
    assert len(customer.search_customers("asha")) == 1
    assert customer.search_customers("nobody") == []


def test_update_customer():
    cid = new_customer()
    customer.update_customer(cid, name="Asha R", email="", phone="")
    row = customer.get_customer(cid)
    assert row["name"] == "Asha R"
    assert row["email"] == "asha@example.com"


def test_view_missing_customer():
    with pytest.raises(BankError):
        customer.get_customer(999)


# ---------- accounts ----------

def test_create_account_with_opening_deposit():
    cid = new_customer()
    result = account.create_account(cid, "savings", "250.50")
    assert balance(result["account_number"]) == Decimal("250.50")
    history = transaction.get_history(result["account_number"])
    assert len(history) == 1 and history[0]["transaction_type"] == "DEPOSIT"


def test_account_for_missing_customer():
    with pytest.raises(BankError):
        account.create_account(999, "SAVINGS")


def test_invalid_account_type():
    cid = new_customer()
    with pytest.raises(BankError):
        account.create_account(cid, "GOLD")


def test_account_numbers_are_unique():
    cid = new_customer()
    numbers = {account.create_account(cid, "SAVINGS")["account_number"] for _ in range(5)}
    assert len(numbers) == 5


def test_duplicate_account_number_blocked_by_database():
    cid = new_customer()
    number = account.create_account(cid, "SAVINGS")["account_number"]
    with pytest.raises(mysql.connector.Error):
        with db_transaction() as conn:
            execute(conn, "INSERT INTO accounts (customer_id, account_number, "
                          "account_type) VALUES (%s, %s, 'SAVINGS')", (cid, number))


def test_accounts_of_customer():
    cid = new_customer()
    account.create_account(cid, "SAVINGS")
    account.create_account(cid, "CURRENT")
    assert len(account.list_accounts_for_customer(cid)) == 2


# ---------- deposit ----------

def test_deposit_updates_balance_and_history(two_accounts):
    first, _ = two_accounts
    assert transaction.deposit(first, "200.25") == Decimal("1200.25")
    latest = transaction.get_history(first)[0]
    assert latest["transaction_type"] == "DEPOSIT"
    assert latest["amount"] == Decimal("200.25")


@pytest.mark.parametrize("bad", ["0", "-5", "abc", "", "1.234"])
def test_deposit_rejects_bad_amounts(two_accounts, bad):
    first, _ = two_accounts
    with pytest.raises(BankError):
        transaction.deposit(first, bad)
    assert balance(first) == Decimal("1000.00")


def test_deposit_unknown_account():
    with pytest.raises(BankError):
        transaction.deposit("0000000000", "10")


# ---------- withdrawal ----------

def test_withdraw_updates_balance_and_history(two_accounts):
    first, _ = two_accounts
    assert transaction.withdraw(first, "400") == Decimal("600.00")
    assert transaction.get_history(first)[0]["transaction_type"] == "WITHDRAWAL"


def test_withdraw_rejects_bad_amounts(two_accounts):
    first, _ = two_accounts
    for bad in ("0", "-1"):
        with pytest.raises(BankError):
            transaction.withdraw(first, bad)


def test_withdraw_more_than_balance(two_accounts):
    first, _ = two_accounts
    with pytest.raises(BankError, match="Insufficient"):
        transaction.withdraw(first, "1000.01")
    assert balance(first) == Decimal("1000.00")


def test_withdraw_exact_balance(two_accounts):
    first, _ = two_accounts
    assert transaction.withdraw(first, "1000") == Decimal("0.00")


# ---------- transfer ----------

def test_transfer_moves_money_and_records_it(two_accounts):
    first, second = two_accounts
    result = transaction.transfer(first, second, "300")
    assert result["from_balance"] == Decimal("700.00")
    assert result["to_balance"] == Decimal("800.00")
    assert count_rows("transfers") == 1
    assert len(transaction.get_transfer_history(second)) == 1


def test_transfer_same_account(two_accounts):
    first, _ = two_accounts
    with pytest.raises(BankError, match="different"):
        transaction.transfer(first, first, "10")


def test_transfer_unknown_account(two_accounts):
    first, _ = two_accounts
    with pytest.raises(BankError):
        transaction.transfer(first, "0000000000", "10")
    with pytest.raises(BankError):
        transaction.transfer("0000000000", first, "10")


def test_transfer_insufficient_balance(two_accounts):
    first, second = two_accounts
    with pytest.raises(BankError, match="Insufficient"):
        transaction.transfer(first, second, "5000")
    assert balance(first) == Decimal("1000.00")
    assert balance(second) == Decimal("500.00")
    assert count_rows("transfers") == 0


def test_transfer_rolls_back_on_error(two_accounts, monkeypatch):
    """Fail after the debit and credit were done; nothing may be saved."""
    first, second = two_accounts

    def broken(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(transaction, "_insert_transfer_record", broken)
    with pytest.raises(RuntimeError):
        transaction.transfer(first, second, "300")

    assert balance(first) == Decimal("1000.00")
    assert balance(second) == Decimal("500.00")
    assert count_rows("transfers") == 0


# ---------- database constraints ----------

def test_foreign_key_blocks_invalid_account():
    with pytest.raises(mysql.connector.Error):
        with db_transaction() as conn:
            execute(conn, "INSERT INTO accounts (customer_id, account_number, "
                          "account_type) VALUES (999, '1', 'SAVINGS')")


def test_balance_cannot_go_negative(two_accounts):
    first, _ = two_accounts
    with pytest.raises(mysql.connector.Error):
        with db_transaction() as conn:
            execute(conn, "UPDATE accounts SET balance = -1 WHERE account_number = %s",
                    (first,))


def test_transaction_amount_must_be_positive(two_accounts):
    first, _ = two_accounts
    acc_id = account.get_account_by_number(first)["account_id"]
    for bad in (0, -5):
        with pytest.raises(mysql.connector.Error):
            with db_transaction() as conn:
                execute(conn, "INSERT INTO transactions (account_id, transaction_type, "
                              "amount) VALUES (%s, 'DEPOSIT', %s)", (acc_id, bad))


# ---------- reports ----------

def test_reports(two_accounts):
    first, second = two_accounts
    transaction.deposit(first, "200")
    transaction.withdraw(first, "50")
    acc_id = account.get_account_by_number(first)["account_id"]

    assert queries.total_deposits(acc_id) == Decimal("1200.00")
    assert queries.total_withdrawals(acc_id) == Decimal("50.00")
    assert queries.transaction_count(acc_id) == 3

    by_type = {r["transaction_type"]: r["transaction_count"]
               for r in queries.transactions_by_type()}
    assert by_type == {"DEPOSIT": 3, "WITHDRAWAL": 1}

    summary = queries.customer_account_summary()
    assert summary[0]["total_accounts"] == 2
    assert summary[0]["total_balance"] == Decimal("1650.00")
    assert len(queries.recent_transactions(10)) == 4


def test_customer_without_accounts_in_summary():
    new_customer()
    row = queries.customer_account_summary()[0]
    assert row["total_accounts"] == 0
    assert row["total_balance"] == Decimal("0")
