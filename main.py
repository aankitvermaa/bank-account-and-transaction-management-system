"""Command-line menu for the Bank Account & Transaction Management System."""

from decimal import Decimal

import mysql.connector

import account
import customer
import queries
import transaction
from database import BankError


# ---------- small input/output helpers ----------

def ask(prompt):
    return input(prompt).strip()


def ask_int(prompt):
    value = ask(prompt)
    try:
        return int(value)
    except ValueError:
        raise BankError("Please enter a whole number.")


def fmt(value):
    if value is None:
        return "-"
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    return str(value)


def print_table(rows, columns):
    """columns is a list of (heading, key) pairs."""
    if not rows:
        print("  (no records)")
        return
    widths = [
        max(len(heading), *(len(fmt(row[key])) for row in rows))
        for heading, key in columns
    ]
    line = "  ".join(h.ljust(w) for (h, _), w in zip(columns, widths))
    print(line)
    print("-" * len(line))
    for row in rows:
        print("  ".join(fmt(row[k]).ljust(w) for (_, k), w in zip(columns, widths)))


def print_record(row, fields):
    for label, key in fields:
        print(f"  {label:<15}: {fmt(row[key])}")


CUSTOMER_COLUMNS = [("ID", "customer_id"), ("Name", "name"),
                    ("Email", "email"), ("Phone", "phone")]
ACCOUNT_COLUMNS = [("Account No", "account_number"), ("Owner", "customer_name"),
                   ("Type", "account_type"), ("Balance", "balance")]


# ---------- customer screens ----------

def add_customer_screen():
    name = ask("Name: ")
    email = ask("Email: ")
    phone = ask("Phone (10-15 digits): ")
    customer_id = customer.add_customer(name, email, phone)
    print(f"Customer added. Customer ID = {customer_id}")


def view_customer_screen():
    customer_id = ask_int("Customer ID: ")
    row = customer.get_customer(customer_id)
    print_record(row, [("Customer ID", "customer_id"), ("Name", "name"),
                       ("Email", "email"), ("Phone", "phone"),
                       ("Joined", "created_at")])
    print("\nAccounts:")
    print_table(queries.customer_with_accounts(customer_id),
                [("Account No", "account_number"), ("Type", "account_type"),
                 ("Balance", "balance")])


def search_customer_screen():
    rows = customer.search_customers(ask("Search by name, email or phone: "))
    print_table(rows, CUSTOMER_COLUMNS)


def update_customer_screen():
    customer_id = ask_int("Customer ID: ")
    current = customer.get_customer(customer_id)
    print("Press Enter to keep the current value.")
    name = ask(f"Name [{current['name']}]: ")
    email = ask(f"Email [{current['email']}]: ")
    phone = ask(f"Phone [{current['phone']}]: ")
    customer.update_customer(customer_id, name, email, phone)
    print("Customer updated.")


def list_customers_screen():
    print_table(customer.list_customers(), CUSTOMER_COLUMNS)


# ---------- account screens ----------

def create_account_screen():
    customer_id = ask_int("Customer ID: ")
    account_type = ask("Account type (SAVINGS / CURRENT): ")
    opening = ask("Opening deposit (0 for none): ") or "0"
    result = account.create_account(customer_id, account_type, opening)
    print(f"Account created. Account number = {result['account_number']}")


def view_account_screen():
    row = account.get_account_by_number(ask("Account number: "))
    print_record(row, [("Account number", "account_number"),
                       ("Owner", "customer_name"), ("Customer ID", "customer_id"),
                       ("Type", "account_type"), ("Balance", "balance"),
                       ("Opened", "created_at")])


def search_account_screen():
    rows = account.search_accounts(ask("Search by account number or owner name: "))
    print_table(rows, ACCOUNT_COLUMNS)


def balance_screen():
    number = ask("Account number: ")
    print(f"Current balance: {account.get_balance(number):,.2f}")


def customer_accounts_screen():
    rows = account.list_accounts_for_customer(ask_int("Customer ID: "))
    print_table(rows, ACCOUNT_COLUMNS)


# ---------- transaction screens ----------

def deposit_screen():
    number = ask("Account number: ")
    amount = ask("Amount to deposit: ")
    note = ask("Description (optional): ")
    balance = transaction.deposit(number, amount, note)
    print(f"Deposit successful. New balance: {balance:,.2f}")


def withdraw_screen():
    number = ask("Account number: ")
    amount = ask("Amount to withdraw: ")
    note = ask("Description (optional): ")
    balance = transaction.withdraw(number, amount, note)
    print(f"Withdrawal successful. New balance: {balance:,.2f}")


def transfer_screen():
    sender = ask("Sender account number: ")
    receiver = ask("Receiver account number: ")
    amount = ask("Amount to transfer: ")
    note = ask("Description (optional): ")
    result = transaction.transfer(sender, receiver, amount, note)
    print("Transfer successful.")
    print(f"  Sender balance  : {result['from_balance']:,.2f}")
    print(f"  Receiver balance: {result['to_balance']:,.2f}")


def history_screen():
    number = ask("Account number: ")
    print("\nDeposits and withdrawals:")
    print_table(transaction.get_history(number),
                [("Date", "transaction_date"), ("Type", "transaction_type"),
                 ("Amount", "amount"), ("Description", "description")])
    print("\nTransfers:")
    print_table(transaction.get_transfer_history(number),
                [("Date", "transfer_date"), ("From", "from_account"),
                 ("To", "to_account"), ("Amount", "amount"),
                 ("Description", "description")])


# ---------- report screens ----------

def account_report_screen():
    acc = account.get_account_by_number(ask("Account number: "))
    account_id = acc["account_id"]
    print(f"\nReport for account {acc['account_number']} ({acc['customer_name']})")
    print(f"  Current balance    : {acc['balance']:,.2f}")
    print(f"  Total deposits     : {queries.total_deposits(account_id):,.2f}")
    print(f"  Total withdrawals  : {queries.total_withdrawals(account_id):,.2f}")
    print(f"  Transaction count  : {queries.transaction_count(account_id)}")


def recent_transactions_screen():
    print_table(queries.recent_transactions(10),
                [("Date", "transaction_date"), ("Account", "account_number"),
                 ("Type", "transaction_type"), ("Amount", "amount"),
                 ("Description", "description")])


def transactions_by_type_screen():
    print_table(queries.transactions_by_type(),
                [("Type", "transaction_type"), ("Count", "transaction_count"),
                 ("Total amount", "total_amount")])


def customer_summary_screen():
    print_table(queries.customer_account_summary(),
                [("ID", "customer_id"), ("Name", "name"),
                 ("Accounts", "total_accounts"), ("Total balance", "total_balance")])


# ---------- menus ----------

def run_menu(title, options, back_label="Back"):
    while True:
        print(f"\n===== {title} =====")
        for number, (label, _) in enumerate(options, start=1):
            print(f"{number}. {label}")
        print(f"0. {back_label}")

        choice = ask("Choose an option: ")
        if choice == "0":
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(options):
            print("Invalid choice, try again.")
            continue
        try:
            options[int(choice) - 1][1]()
        except BankError as err:
            print(f"Error: {err}")
        except mysql.connector.Error as err:
            print(f"Database error: {err}")


CUSTOMER_MENU = [
    ("Add customer", add_customer_screen),
    ("View customer", view_customer_screen),
    ("Search customers", search_customer_screen),
    ("Update customer", update_customer_screen),
    ("List all customers", list_customers_screen),
]

ACCOUNT_MENU = [
    ("Create account", create_account_screen),
    ("View account", view_account_screen),
    ("Search accounts", search_account_screen),
    ("Check balance", balance_screen),
    ("Accounts of a customer", customer_accounts_screen),
]

TRANSACTION_MENU = [
    ("Deposit", deposit_screen),
    ("Withdraw", withdraw_screen),
    ("Transfer", transfer_screen),
    ("Transaction history", history_screen),
]

REPORT_MENU = [
    ("Account report", account_report_screen),
    ("Recent transactions", recent_transactions_screen),
    ("Transactions by type", transactions_by_type_screen),
    ("Customer account summary", customer_summary_screen),
]

MAIN_MENU = [
    ("Customers", lambda: run_menu("Customers", CUSTOMER_MENU)),
    ("Accounts", lambda: run_menu("Accounts", ACCOUNT_MENU)),
    ("Transactions", lambda: run_menu("Transactions", TRANSACTION_MENU)),
    ("Reports", lambda: run_menu("Reports", REPORT_MENU)),
]


def main():
    print("Bank Account & Transaction Management System")
    try:
        run_menu("Main Menu", MAIN_MENU, back_label="Exit")
    except (KeyboardInterrupt, EOFError):
        print()
    print("Goodbye.")


if __name__ == "__main__":
    main()
