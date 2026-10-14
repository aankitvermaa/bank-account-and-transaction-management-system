"""Read-only SQL queries used for lookups and reports."""

from database import fetch_all, fetch_one

CUSTOMER_WITH_ACCOUNTS = """
    SELECT c.customer_id, c.name, a.account_number, a.account_type, a.balance
    FROM customers c
    JOIN accounts a ON c.customer_id = a.customer_id
    WHERE c.customer_id = %s
    ORDER BY a.account_id
"""

TRANSACTION_HISTORY = """
    SELECT transaction_type, amount, transaction_date, description
    FROM transactions
    WHERE account_id = %s
    ORDER BY transaction_date DESC, transaction_id DESC
    LIMIT %s
"""

TRANSFER_HISTORY = """
    SELECT t.transfer_date, fa.account_number AS from_account,
           ta.account_number AS to_account, t.amount, t.description
    FROM transfers t
    JOIN accounts fa ON t.from_account_id = fa.account_id
    JOIN accounts ta ON t.to_account_id = ta.account_id
    WHERE t.from_account_id = %s OR t.to_account_id = %s
    ORDER BY t.transfer_date DESC, t.transfer_id DESC
    LIMIT %s
"""

TOTAL_BY_TYPE = """
    SELECT COALESCE(SUM(amount), 0) AS total
    FROM transactions
    WHERE account_id = %s AND transaction_type = %s
"""

TRANSACTION_COUNT = """
    SELECT COUNT(*) AS total FROM transactions WHERE account_id = %s
"""

COUNT_BY_TYPE = """
    SELECT transaction_type, COUNT(*) AS transaction_count,
           COALESCE(SUM(amount), 0) AS total_amount
    FROM transactions
    GROUP BY transaction_type
    ORDER BY transaction_type
"""

RECENT_TRANSACTIONS = """
    SELECT t.transaction_date, a.account_number, t.transaction_type,
           t.amount, t.description
    FROM transactions t
    JOIN accounts a ON t.account_id = a.account_id
    ORDER BY t.transaction_date DESC, t.transaction_id DESC
    LIMIT %s
"""

CUSTOMER_SUMMARY = """
    SELECT c.customer_id, c.name,
           COUNT(a.account_id) AS total_accounts,
           COALESCE(SUM(a.balance), 0) AS total_balance
    FROM customers c
    LEFT JOIN accounts a ON c.customer_id = a.customer_id
    GROUP BY c.customer_id, c.name
    ORDER BY c.customer_id
"""


def customer_with_accounts(customer_id):
    return fetch_all(CUSTOMER_WITH_ACCOUNTS, (customer_id,))


def transaction_history(account_id, limit=20):
    return fetch_all(TRANSACTION_HISTORY, (account_id, limit))


def transfer_history(account_id, limit=20):
    return fetch_all(TRANSFER_HISTORY, (account_id, account_id, limit))


def total_deposits(account_id):
    return fetch_one(TOTAL_BY_TYPE, (account_id, "DEPOSIT"))["total"]


def total_withdrawals(account_id):
    return fetch_one(TOTAL_BY_TYPE, (account_id, "WITHDRAWAL"))["total"]


def transaction_count(account_id):
    return fetch_one(TRANSACTION_COUNT, (account_id,))["total"]


def transactions_by_type():
    return fetch_all(COUNT_BY_TYPE)


def recent_transactions(limit=10):
    return fetch_all(RECENT_TRANSACTIONS, (limit,))


def customer_account_summary():
    return fetch_all(CUSTOMER_SUMMARY)
