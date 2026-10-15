import sqlite3
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

DB_PATH = "payments.db"

def run_audits():
    conn = sqlite3.connect(DB_PATH)

    print("\n" + "="*80)
    print("QUERY 1: DAILY SETTLEMENT & NET PAYOUT SUMMARY (TOP 5 ROWS)")
    print("="*80)
    q1 = """
    SELECT 
        DATE(ft.transaction_timestamp) AS settlement_date,
        dm.merchant_name,
        dm.category,
        COUNT(ft.transaction_id) AS settled_volume,
        ROUND(SUM(ft.amount_cents) / 100.0, 2) AS gross_settled_usd,
        ROUND(SUM(ft.fee_cents) / 100.0, 2) AS processing_fees_usd,
        ROUND(SUM(ft.net_cents) / 100.0, 2) AS net_merchant_payout_usd
    FROM fact_transactions ft
    JOIN dim_merchants dm ON ft.merchant_id = dm.merchant_id
    WHERE ft.status = 'settled'
    GROUP BY settlement_date, dm.merchant_name, dm.category
    ORDER BY settlement_date DESC, gross_settled_usd DESC
    LIMIT 5;
    """
    df1 = pd.read_sql_query(q1, conn)
    print(df1.to_string(index=False))

    print("\n" + "="*80)
    print("QUERY 2: ROLLING 7-DAY NET PAYOUT (WINDOW FUNCTION - TOP 5 ROWS)")
    print("="*80)
    q2 = """
    WITH daily_merchant_totals AS (
        SELECT 
            DATE(transaction_timestamp) AS txn_date,
            merchant_id,
            SUM(net_cents) / 100.0 AS daily_net_usd
        FROM fact_transactions
        WHERE status = 'settled'
        GROUP BY DATE(transaction_timestamp), merchant_id
    )
    SELECT 
        txn_date,
        merchant_id,
        ROUND(daily_net_usd, 2) AS net_payout_usd,
        ROUND(AVG(daily_net_usd) OVER (
            PARTITION BY merchant_id 
            ORDER BY txn_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 2) AS rolling_7d_avg_net_usd
    FROM daily_merchant_totals
    ORDER BY merchant_id, txn_date DESC
    LIMIT 5;
    """
    df2 = pd.read_sql_query(q2, conn)
    print(df2.to_string(index=False))

    print("\n" + "="*80)
    print("QUERY 3: QUARANTINE AUDIT (ANOMALY BREAKDOWN)")
    print("="*80)
    q3 = """
    SELECT 
        rejection_reason,
        COUNT(*) AS incident_count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM quarantine_transactions), 2) AS pct_of_total_errors
    FROM quarantine_transactions
    GROUP BY rejection_reason
    ORDER BY incident_count DESC;
    """
    df3 = pd.read_sql_query(q3, conn)
    print(df3.to_string(index=False))

    conn.close()

if __name__ == "__main__":
    run_audits()