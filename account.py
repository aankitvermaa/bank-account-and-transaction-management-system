"""Account operations: create, find, search, balance, per-customer listing."""

import random
from decimal import Decimal, InvalidOperation

from database import BankError, db_transaction, execute, fetch_all, fetch_one
from customer import get_customer

ACCOUNT_TYPES = ("SAVINGS", "CURRENT")
MAX_AMOUNT = Decimal("9999999999.99")  # largest value DECIMAL(12,2) can hold

_ACCOUNT_SELECT = (
    "SELECT a.account_id, a.customer_id, c.name AS customer_name, "
    "a.account_number, a.account_type, a.balance, a.created_at "
    "FROM accounts a JOIN customers c ON a.customer_id = c.customer_id "
)


def parse_amount(value, allow_zero=False):
    """Convert user input to a Decimal money value and validate it."""
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise BankError("Amount must be a number.")

    if not amount.is_finite():
        raise BankError("Amount must be a number.")
    if amount.as_tuple().exponent < -2:
        raise BankError("Amount can have at most 2 decimal places.")
    if amount < 0 or (amount == 0 and not allow_zero):
        raise BankError("Amount must be greater than zero.")
    if amount > MAX_AMOUNT:
        raise BankError("Amount is too large.")
    return amount


def _generate_account_number(conn):
    """Make a random 10-digit account number that is not already used."""
    while True:
        number = str(random.randint(10**9, 10**10 - 1))
        exists = fetch_one(
            "SELECT 1 AS found FROM accounts WHERE account_number = %s",
            (number,),
            conn,
        )
        if exists is None:
            return number


def create_account(customer_id, account_type, opening_deposit=0):
    """Create an account for an existing customer.

    A non-zero opening deposit is also recorded as a DEPOSIT transaction so
    the history always adds up to the balance.
    Returns a dict with account_id and account_number.
    """
    account_type = (account_type or "").strip().upper()
    if account_type not in ACCOUNT_TYPES:
        raise BankError("Account type must be SAVINGS or CURRENT.")
    opening = parse_amount(opening_deposit, allow_zero=True)

    with db_transaction() as conn:
        get_customer(customer_id, conn)  # customer must exist
        number = _generate_account_number(conn)
        account_id = execute(
            conn,
            "INSERT INTO accounts (customer_id, account_number, account_type, balance) "
            "VALUES (%s, %s, %s, %s)",
            (customer_id, number, account_type, opening),
        )
        if opening > 0:
            execute(
                conn,
                "INSERT INTO transactions "
                "(account_id, transaction_type, amount, description) "
                "VALUES (%s, 'DEPOSIT', %s, 'Opening deposit')",
                (account_id, opening),
            )
    return {"account_id": account_id, "account_number": number}


def get_account_by_number(account_number, conn=None):
    """Return the account (with owner name); raises BankError if missing."""
    account_number = (account_number or "").strip()
    if not account_number:
        raise BankError("Account number is required.")
    row = fetch_one(
        _ACCOUNT_SELECT + "WHERE a.account_number = %s", (account_number,), conn
    )
    if row is None:
        raise BankError(f"Account {account_number} does not exist.")
    return row


def get_balance(account_number):
    return get_account_by_number(account_number)["balance"]


def search_accounts(keyword):
    """Find accounts by account number or owner name."""
    keyword = (keyword or "").strip()
    if not keyword:
        raise BankError("Search text is required.")
    pattern = f"%{keyword}%"
    return fetch_all(
        _ACCOUNT_SELECT
        + "WHERE a.account_number LIKE %s OR c.name LIKE %s "
        "ORDER BY a.account_id",
        (pattern, pattern),
    )


def list_accounts_for_customer(customer_id):
    get_customer(customer_id)  # customer must exist
    return fetch_all(
        _ACCOUNT_SELECT + "WHERE a.customer_id = %s ORDER BY a.account_id",
        (customer_id,),
    )
