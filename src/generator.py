import json
import random
import uuid
from datetime import datetime, timedelta

def generate_mock_webhooks(output_path="data/raw_webhooks.json", count=1000):
    merchants = ["m_swivel_01", "m_swivel_02", "m_swivel_03", "m_swivel_04", "m_swivel_05"]
    methods = ["pm_visa_01", "pm_mc_01", "pm_amex_01", "pm_ach_01"]
    statuses = ["settled", "settled", "settled", "authorized", "refunded", "failed"]

    base_time = datetime(2026, 10, 1, 8, 0, 0)
    events = []

    for i in range(count):
        tx_id = f"tx_{uuid.uuid4().hex[:12]}"
        timestamp = base_time + timedelta(minutes=random.randint(1, 20000))

        event = {
            "transaction_id": tx_id,
            "merchant_id": random.choice(merchants),
            "method_id": random.choice(methods),
            "amount_cents": random.randint(500, 75000), # $5.00 to $750.00
            "status": random.choice(statuses),
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Inject realistic pipeline edge cases
        if i % 50 == 0:
            # Duplicate transaction ID (network retry anomaly)
            events.append(events[-1].copy() if events else event)
        elif i % 80 == 0:
            # Corrupted amount
            event["amount_cents"] = -2500
            events.append(event)
        elif i % 120 == 0:
            # Missing status field
            event["status"] = None
            events.append(event)
        else:
            events.append(event)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

    print(f" Generated {len(events)} synthetic payment webhooks at {output_path}")

if __name__ == "__main__":
    generate_mock_webhooks()