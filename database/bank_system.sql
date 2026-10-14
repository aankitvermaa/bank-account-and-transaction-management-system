-- Bank Account & Transaction Management System
-- Schema + sample data (MySQL 8.0.16 or newer, needed for CHECK constraints)
-- WARNING: this script drops and recreates the four tables.

CREATE DATABASE IF NOT EXISTS bank_system;
USE bank_system;

DROP TABLE IF EXISTS transfers;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    account_number VARCHAR(20) NOT NULL UNIQUE,
    account_type VARCHAR(20) NOT NULL,
    balance DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_account_balance
        CHECK (balance >= 0),

    CONSTRAINT fk_account_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(255),

    CONSTRAINT chk_transaction_amount
        CHECK (amount > 0),

    CONSTRAINT fk_transaction_account
        FOREIGN KEY (account_id)
        REFERENCES accounts(account_id)
);

CREATE TABLE transfers (
    transfer_id INT AUTO_INCREMENT PRIMARY KEY,
    from_account_id INT NOT NULL,
    to_account_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    transfer_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(255),

    CONSTRAINT chk_transfer_amount
        CHECK (amount > 0),

    CONSTRAINT fk_transfer_sender
        FOREIGN KEY (from_account_id)
        REFERENCES accounts(account_id),

    CONSTRAINT fk_transfer_receiver
        FOREIGN KEY (to_account_id)
        REFERENCES accounts(account_id)
);

CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transfers_sender ON transfers(from_account_id);
CREATE INDEX idx_transfers_receiver ON transfers(to_account_id);

-- Sample data (balances match the recorded transactions and transfer)
INSERT INTO customers (name, email, phone) VALUES
    ('Rahul Verma', 'rahul.verma@example.com', '9810012345'),
    ('Priya Sharma', 'priya.sharma@example.com', '9899054321'),
    ('Amit Singh', 'amit.singh@example.com', '9711098765');

INSERT INTO accounts (customer_id, account_number, account_type, balance) VALUES
    (1, '1000000001', 'SAVINGS', 35000.00),
    (1, '1000000002', 'CURRENT', 20000.00),
    (2, '1000000003', 'SAVINGS', 40000.00);

INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES
    (1, 'DEPOSIT', 50000.00, 'Opening deposit'),
    (1, 'WITHDRAWAL', 5000.00, 'ATM withdrawal'),
    (2, 'DEPOSIT', 20000.00, 'Opening deposit'),
    (3, 'DEPOSIT', 30000.00, 'Opening deposit');

INSERT INTO transfers (from_account_id, to_account_id, amount, description) VALUES
    (1, 3, 10000.00, 'Rent payment');
