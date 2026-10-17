# FinTech Payment Ingestion & Automated Reconciliation Engine

An end-to-end data engineering pipeline designed to ingest, validate, and reconcile high-volume payment gateway webhooks. Built with Python, SQLite, Pandas, and advanced SQL window functions.

## Pipeline Architecture & Execution Stages

1. **Raw Event Ingestion (src/generator.py)**
   * Simulates high-velocity webhook payloads containing credit, debit, and ACH transactions.
   * Introduces realistic data anomalies: network duplicate retries, non-positive amounts, and malformed status flags.

2. **Validation & Cleansing Pipeline (src/ingest_pipeline.py)**
   * **Idempotency Verification:** Tracks transaction IDs in-memory and enforces primary key constraints at the database level to prevent duplicate ledger entries.
   * **Data Quality Checks:** Evaluates records against strict business rules (positive integer amounts, supported payment rails, recognized status codes).
   * **Automated Fee Engine:** Computes transaction fees (2.9% + $0.30) on settled records and calculates net payouts in integer cents to eliminate floating-point rounding errors.
   * **Dead-Letter Quarantine:** Diverts invalid payloads into a separate quarantine table alongside explicit audit failure reasons.

3. **Relational Storage (sql/schema.sql)**
   * **fact_transactions**: Stores clean, staged transactions partitioned by status and timestamp.
   * **dim_merchants**: Normalizes merchant entities, names, and industry categories.
   * **dim_payment_methods**: Maps payment types (credit, debit, ach) and networks (Visa, Mastercard, Amex).
   * **quarantine_transactions**: Maintains a full audit log of corrupted records for root-cause analysis.

4. **Financial Reconciliation & Auditing (sql/reconciliation.sql / src/run_audit.py)**
   * **Daily Settlement Totals:** Aggregates gross volume, processor fees, and net payouts per merchant.
   * **Rolling 7-Day Window Analysis:** Uses SQL window functions (OVER (PARTITION BY ... ROWS BETWEEN ...)) to identify volume trends and cash-flow velocity.
   * **Anomaly Distribution Profiling:** Calculates error percentages across failure categories to inform upstream API validation improvements.

## Database Schema Design

* **dim_merchants**
  * merchant_id (TEXT, PK)
  * merchant_name (TEXT)
  * category (TEXT)

* **dim_payment_methods**
  * method_id (TEXT, PK)
  * payment_type (TEXT)
  * network (TEXT)

* **fact_transactions**
  * transaction_id (TEXT, PK)
  * merchant_id (TEXT, FK)
  * method_id (TEXT, FK)
  * amount_cents (INTEGER)
  * fee_cents (INTEGER)
  * net_cents (INTEGER)
  * status (TEXT)
  * transaction_timestamp (TIMESTAMP)

* **quarantine_transactions**
  * raw_payload (TEXT)
  * rejection_reason (TEXT)
  * flagged_at (TIMESTAMP)

## Prerequisites & Dependencies

* Python 3.9+
* Required packages:
    pip install pandas

## How to Run

1. Clone repository & open folder:
    git clone https://github.com/AaronIGW/payment_data_pipeline.git
    cd payment_data_pipeline

2. Generate synthetic webhook payloads:
    python src/generator.py
   (Generates 1,000 synthetic transaction records with intentional anomalies in data/raw_webhooks.json)

3. Run ingestion pipeline:
    python src/ingest_pipeline.py
   (Initializes payments.db, seeds dimensions, stages valid records to fact_transactions, and routes corrupted records to quarantine_transactions)

4. Run financial reconciliation audits:
    python src/run_audit.py
   (Executes daily settlement summaries, rolling 7-day trailing net payouts via window functions, and prints dead-letter anomaly breakdown tables)
