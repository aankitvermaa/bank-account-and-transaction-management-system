# Bank Account and Transaction Management System

This is a small command-line banking program I built with Python and MySQL as
part of my B.Tech coursework practice. I wanted a project where the database
design actually matters, so instead of a simple CRUD app I picked a problem where
money moves between records and the data has to stay correct. It is a learning
project and is not meant to handle real money.

## What it does

You run it in the terminal and pick options from a menu. From there you can:

- add, view, search, update and list customers
- open a savings or current account for a customer (with an optional opening deposit)
- look up accounts by number or owner name and check balances
- deposit, withdraw, and transfer money between two accounts
- see the history of an account
- view a few reports: totals for an account, recent activity, number of transactions by type, and a per-customer summary of accounts and balances

The program checks input before touching the database. Amounts must be positive
with at most two decimal places, a withdrawal or transfer cannot be more than the
balance, an account cannot transfer to itself, required customer fields cannot be
blank, and email, phone and account numbers cannot repeat.

## Tools used

Python 3, MySQL 8.0.16 or newer (older versions ignore CHECK constraints),
`mysql-connector-python` and `python-dotenv`. `pytest` is only used for the tests.

## How the code is organised

```text
main.py            menus and input/output only
database.py        connection, commit/rollback, small query helpers
customer.py        customer functions
account.py         account functions and amount checking
transaction.py     deposit, withdraw, transfer, history
queries.py         SQL used for reports and lookups
database/bank_system.sql   tables, indexes and sample data
tests/             pytest tests
```

I kept the SQL out of `main.py` on purpose, so the menu code only calls
functions and prints the result.

## Database design

There are four tables.

- `customers` holds name, email and phone. Email and phone are unique.
- `accounts` holds account number, type and balance. Each account belongs to one customer.
- `transactions` holds the deposits and withdrawals of an account.
- `transfers` holds money sent from one account to another.

One customer can have many accounts, and one account can have many
transactions. A transfer links two rows of the accounts table, a sender and a
receiver.

```text
customers  1 --- N  accounts  1 --- N  transactions

accounts (sender) --- transfers --- accounts (receiver)
```

I stored customer details only once and linked everything else through keys.
If the name and email were copied into every transaction row, a single change
of email would mean updating hundreds of rows, and the copies could end up
disagreeing. Foreign keys make sure an account cannot point to a customer that
does not exist. CHECK constraints stop a balance from going below zero and stop
zero or negative amounts. Money columns are `DECIMAL(12,2)` because floating
point numbers cannot represent values like 0.10 exactly.

The transfer is the part I spent most time on. Subtracting from one account,
adding to another and saving the transfer record must either all happen or not
happen at all. In `database.py` there is a small helper, `db_transaction()`,
that commits when the block finishes normally and rolls back if anything raises
an error. The transfer function runs inside it. One of the tests forces an
error after the balances have been changed and checks that both balances are
back to their old values.

## Setting it up

1. Install Python, MySQL and Git, and make sure the MySQL service is running.
2. Get the code and create a virtual environment:
3. Create the database and load the sample data. This drops and recreates the four tables, so do not run it on data you want to keep.

## Running it

```bash
python main.py
```

The sample data has three customers and three accounts (`1000000001`,
`1000000002`, `1000000003`) so you can try transfers straight away. A good first
run is: create a customer, open an account for them with an opening deposit,
transfer some money from `1000000001` to the new account, then look at the
history and the customer summary report. Also try a few bad inputs, like a
negative amount or withdrawing too much, to see the error messages.

## Tests

```bash
python -m pytest -v
```

The tests build their own database called `bank_system_test` from the same SQL
file, so the real data is never touched (the MySQL user needs permission to
create databases). They check normal and invalid input, duplicate values,
insufficient balance, the database constraints, the reports, and the transfer
rollback described above.

## SQL used

Most of the queries are in `queries.py`:

- JOIN to list a customer together with their accounts
- WHERE and ORDER BY for an account's history, newest first
- SUM with COALESCE for total deposits and withdrawals, so an empty account gives 0 instead of NULL
- GROUP BY with COUNT for the number of transactions of each type
- LEFT JOIN with GROUP BY for the customer summary, so customers who have no account still appear

Every query uses `%s` placeholders and passes values separately, so user input
is never joined into the SQL text.

## What I practised

On the database side: table design, normalization, primary and foreign keys,
UNIQUE, NOT NULL and CHECK constraints, one-to-many relationships, indexes on
the foreign key columns, joins, aggregation, and commit and rollback.

On the Python side: splitting a program into modules, writing small functions,
a context manager for transactions, custom exceptions, input validation, working
with `Decimal`, and connecting to MySQL.

## Limitations

- It is single user and has no login.
- Rows are not locked during a transfer, so two programs changing the same account at exactly the same moment are not protected from each other.
- Transfers are stored only in the `transfers` table, not copied into `transactions`, so an account's full history is shown from two tables.
- It is not meant for real financial data.