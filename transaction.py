"""Deposits, withdrawals, transfers and transaction history."""

from account import get_account_by_number, parse_amount
from database import BankError, db_transaction, execute, fetch_one
import queries


def _change_balance(conn, account_id, delta):
    execute(
        conn,
        "UPDATE accounts SET balance = balance + %s WHERE account_id = %s",
        (delta, account_id),
    )


def _insert_transaction(conn, account_id, kind, amount, description):
    execute(
        conn,
        "INSERT INTO transactions "
        "(account_id, transaction_type, amount, description) "
        "VALUES (%s, %s, %s, %s)",
        (account_id, kind, amount, description),
    )


def _insert_transfer_record(conn, from_id, to_id, amount, description):
    execute(
        conn,
        "INSERT INTO transfers "
        "(from_account_id, to_account_id, amount, description) "
        "VALUES (%s, %s, %s, %s)",
        (from_id, to_id, amount, description),
    )


def _current_balance(conn, account_id):
    row = fetch_one(
        "SELECT balance FROM accounts WHERE account_id = %s", (account_id,), conn
    )
    return row["balance"]


def deposit(account_number, amount, description=None):
    """Add money to an account and record it. Returns the new balance."""
    amount = parse_amount(amount)
    description = (description or "").strip() or "Cash deposit"

    with db_transaction() as conn:
        acc = get_account_by_number(account_number, conn)
        _change_balance(conn, acc["account_id"], amount)
        _insert_transaction(conn, acc["account_id"], "DEPOSIT", amount, description)
        return _current_balance(conn, acc["account_id"])


def withdraw(account_number, amount, description=None):
    """Take money out of an account and record it. Returns the new balance."""
    amount = parse_amount(amount)
    description = (description or "").strip() or "Cash withdrawal"

    with db_transaction() as conn:
        acc = get_account_by_number(account_number, conn)
        if amount > acc["balance"]:
            raise BankError(
                f"Insufficient balance. Available: {acc['balance']:,.2f}"
            )
        _change_balance(conn, acc["account_id"], -amount)
        _insert_transaction(conn, acc["account_id"], "WITHDRAWAL", amount, description)
        return _current_balance(conn, acc["account_id"])


def transfer(from_number, to_number, amount, description=None):
    """Move money between two accounts as one unit of work.

    The debit, the credit and the transfer record are saved together.
    If any step fails, db_transaction() rolls everything back.
    Returns the new balances of both accounts.
    """
    from_number = (from_number or "").strip()
    to_number = (to_number or "").strip()
    if not from_number or not to_number:
        raise BankError("Both sender and receiver account numbers are required.")
    if from_number == to_number:
        raise BankError("Sender and receiver accounts must be different.")
    amount = parse_amount(amount)
    description = (description or "").strip() or "Fund transfer"

    with db_transaction() as conn:
        sender = get_account_by_number(from_number, conn)
        receiver = get_account_by_number(to_number, conn)

        if amount > sender["balance"]:
            raise BankError(
                f"Insufficient balance. Available: {sender['balance']:,.2f}"
            )

        _change_balance(conn, sender["account_id"], -amount)
        _change_balance(conn, receiver["account_id"], amount)
        _insert_transfer_record(
            conn, sender["account_id"], receiver["account_id"], amount, description
        )

        return {
            "from_balance": _current_balance(conn, sender["account_id"]),
            "to_balance": _current_balance(conn, receiver["account_id"]),
        }


def get_history(account_number, limit=20):
    """Latest deposits/withdrawals of an account, newest first."""
    acc = get_account_by_number(account_number)
    return queries.transaction_history(acc["account_id"], limit)


def get_transfer_history(account_number, limit=20):
    """Latest transfers sent or received by an account, newest first."""
    acc = get_account_by_number(account_number)
    return queries.transfer_history(acc["account_id"], limit)
