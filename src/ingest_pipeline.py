import json
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "payments.db"
SCHEMA_PATH = "sql/schema.sql"
RAW_DATA_PATH = "data/raw_webhooks.json"

def init_database(db_path=DB_PATH, schema_path=SCHEMA_PATH):
    """Initializes SQLite database and populates dimension tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Apply DDL schema
    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    # Seed Dimension: Merchants
    merchants = [
        ("m_swivel_01", "Apex Retailers", "Ecommerce"),
        ("m_swivel_02", "Keystone Logistics", "Transportation"),
        ("m_swivel_03", "Liberty Health", "Medical"),
        ("m_swivel_04", "Metro Dining Group", "Hospitality"),
        ("m_swivel_05", "Philly Tech Labs", "SaaS")
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO dim_merchants (merchant_id, merchant_name, category) VALUES (?, ?, ?);",
        merchants
    )

    # Seed Dimension: Payment Methods
    payment_methods = [
        ("pm_visa_01", "credit", "Visa"),
        ("pm_mc_01", "credit", "Mastercard"),
        ("pm_amex_01", "credit", "Amex"),
        ("pm_ach_01", "ach", "NACHA")
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO dim_payment_methods (method_id, payment_type, network) VALUES (?, ?, ?);",
        payment_methods
    )

    conn.commit()
    conn.close()
    print(" Database initialized and dimension tables seeded.")

def run_etl_pipeline(raw_path=RAW_DATA_PATH, db_path=DB_PATH):
    """Ingests raw webhook JSON, enforces data quality rules, and populates tables."""
    with open(raw_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Pre-fetch existing transaction IDs to ensure pipeline idempotency across runs
    cursor.execute("SELECT transaction_id FROM fact_transactions;")
    existing_ids = {row[0] for row in cursor.fetchall()}

    valid_transactions = []
    quarantined_records = []
    seen_in_batch = set()

    VALID_STATUSES = {"authorized", "settled", "refunded", "failed"}

    for item in records:
        tx_id = item.get("transaction_id")
        amount = item.get("amount_cents")
        status = item.get("status")
        raw_dump = json.dumps(item)

        # Rule 1: Missing or Malformed Transaction ID
        if not tx_id:
            quarantined_records.append((raw_dump, "Missing transaction_id"))
            continue

        # Rule 2: Duplicate Transaction ID (Idempotency check)
        if tx_id in existing_ids or tx_id in seen_in_batch:
            quarantined_records.append((raw_dump, f"Duplicate transaction_id: {tx_id}"))
            continue

        # Rule 3: Missing or Non-Positive Amount
        if amount is None or not isinstance(amount, int) or amount <= 0:
            quarantined_records.append((raw_dump, f"Invalid amount_cents: {amount}"))
            continue

        # Rule 4: Invalid Transaction Status
        if status not in VALID_STATUSES:
            quarantined_records.append((raw_dump, f"Invalid transaction status: {status}"))
            continue

        seen_in_batch.add(tx_id)

        # Calculate processing fee: 2.9% + 30 cents on settled charges, otherwise 0
        fee_cents = int(amount * 0.029) + 30 if status == "settled" else 0
        net_cents = amount - fee_cents

        valid_transactions.append((
            tx_id,
            item.get("merchant_id"),
            item.get("method_id"),
            amount,
            fee_cents,
            net_cents,
            status,
            item.get("timestamp")
        ))

    # Bulk insert valid transactions
    if valid_transactions:
        cursor.executemany(
            """
            INSERT INTO fact_transactions (
                transaction_id, merchant_id, method_id,
                amount_cents, fee_cents, net_cents,
                status, transaction_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            valid_transactions
        )

    # Bulk insert quarantined transactions
    if quarantined_records:
        cursor.executemany(
            """
            INSERT INTO quarantine_transactions (raw_payload, rejection_reason)
            VALUES (?, ?);
            """,
            quarantined_records
        )

    conn.commit()
    conn.close()

    print("\n--- ETL Execution Summary ---")
    print(f"Total Raw Records Ingested : {len(records)}")
    print(f"Valid Transactions Staged  : {len(valid_transactions)}")
    print(f"Quarantined Anomalies      : {len(quarantined_records)}")

if __name__ == "__main__":
    init_database()
    run_etl_pipeline()