"""Customer operations: add, view, search, update, list."""

import re

from mysql.connector import IntegrityError, errorcode

from database import BankError, db_transaction, execute, fetch_all, fetch_one

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\d{10,15}$")


def _required(value, label):
    value = (value or "").strip()
    if not value:
        raise BankError(f"{label} is required.")
    return value


def _clean_details(name, email, phone):
    """Validate and tidy the three customer fields."""
    name = _required(name, "Name")
    email = _required(email, "Email").lower()
    phone = _required(phone, "Phone").replace(" ", "").replace("-", "")

    if not EMAIL_PATTERN.match(email):
        raise BankError("Email address is not valid.")
    if not PHONE_PATTERN.match(phone):
        raise BankError("Phone must contain 10 to 15 digits.")
    return name, email, phone


def _duplicate_error(err):
    """Turn a MySQL duplicate-key error into a readable message."""
    text = str(err).lower()
    if "email" in text:
        return BankError("A customer with this email already exists.")
    if "phone" in text:
        return BankError("A customer with this phone number already exists.")
    return BankError("Duplicate value found.")


def add_customer(name, email, phone):
    """Insert a customer and return the new customer_id."""
    name, email, phone = _clean_details(name, email, phone)
    try:
        with db_transaction() as conn:
            return execute(
                conn,
                "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)",
                (name, email, phone),
            )
    except IntegrityError as err:
        if err.errno == errorcode.ER_DUP_ENTRY:
            raise _duplicate_error(err) from err
        raise


def get_customer(customer_id, conn=None):
    """Return one customer; raises BankError if the id does not exist."""
    row = fetch_one(
        "SELECT customer_id, name, email, phone, created_at "
        "FROM customers WHERE customer_id = %s",
        (customer_id,),
        conn,
    )
    if row is None:
        raise BankError(f"No customer found with ID {customer_id}.")
    return row


def search_customers(keyword):
    """Find customers whose name, email or phone contains the keyword."""
    keyword = _required(keyword, "Search text")
    pattern = f"%{keyword}%"
    return fetch_all(
        "SELECT customer_id, name, email, phone FROM customers "
        "WHERE name LIKE %s OR email LIKE %s OR phone LIKE %s "
        "ORDER BY name",
        (pattern, pattern, pattern),
    )


def update_customer(customer_id, name=None, email=None, phone=None):
    """Update the given fields; blank/None fields keep their current value."""
    current = get_customer(customer_id)
    name, email, phone = _clean_details(
        name or current["name"],
        email or current["email"],
        phone or current["phone"],
    )
    try:
        with db_transaction() as conn:
            execute(
                conn,
                "UPDATE customers SET name = %s, email = %s, phone = %s "
                "WHERE customer_id = %s",
                (name, email, phone, customer_id),
            )
    except IntegrityError as err:
        if err.errno == errorcode.ER_DUP_ENTRY:
            raise _duplicate_error(err) from err
        raise


def list_customers():
    return fetch_all(
        "SELECT customer_id, name, email, phone FROM customers ORDER BY customer_id"
    )
