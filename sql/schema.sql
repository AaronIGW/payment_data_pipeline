-- Dimension: Registered Merchants
CREATE TABLE IF NOT EXISTS dim_merchants (
    merchant_id TEXT PRIMARY KEY,
    merchant_name TEXT NOT NULL,
    category TEXT NOT NULL
);

-- Dimension: Payment Methods & Rails
CREATE TABLE IF NOT EXISTS dim_payment_methods (
    method_id TEXT PRIMARY KEY,
    payment_type TEXT NOT NULL,  -- 'credit', 'debit', 'ach'
    network TEXT NOT NULL         -- 'Visa', 'Mastercard', 'Amex'
);

-- Fact: Core Transaction Ledger
CREATE TABLE IF NOT EXISTS fact_transactions (
    transaction_id TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL,
    method_id TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    fee_cents INTEGER NOT NULL,
    net_cents INTEGER NOT NULL,
    status TEXT NOT NULL,         -- 'authorized', 'settled', 'refunded', 'failed'
    transaction_timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (merchant_id) REFERENCES dim_merchants(merchant_id),
    FOREIGN KEY (method_id) REFERENCES dim_payment_methods(method_id)
);

-- Quarantine / Dead-Letter Queue for corrupted data
CREATE TABLE IF NOT EXISTS quarantine_transactions (
    raw_payload TEXT,
    rejection_reason TEXT,
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);