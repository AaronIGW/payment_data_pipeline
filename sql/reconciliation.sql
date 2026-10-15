-- Query 1: Daily Merchant Settlement & Net Payout Summary
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
ORDER BY settlement_date DESC, gross_settled_usd DESC;

-- Query 2: Rolling 7-Day Net Payout by Merchant (Analytical Window Function)
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
ORDER BY merchant_id, txn_date DESC;

-- Query 3: Quarantine Audit - Anomaly Breakdown by Rejection Reason
SELECT 
    rejection_reason,
    COUNT(*) AS incident_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM quarantine_transactions), 2) AS pct_of_total_errors
FROM quarantine_transactions
GROUP BY rejection_reason
ORDER BY incident_count DESC;