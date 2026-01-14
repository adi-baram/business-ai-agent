#!/usr/bin/env python3
"""
Generate sample e-commerce data for the AI Agent take-home assignment.

Usage:
    python generate_data.py

This will create two files in the current directory:
    - customers.csv (200 customers)
    - transactions.csv (5000 transactions)

Note: Transaction dates span the last 12 months from today.
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

CATEGORIES = ["electronics", "clothing", "home", "grocery", "sports"]
REGIONS = ["north", "south", "east", "west"]
SEGMENTS = ["new", "regular", "vip"]


def generate_data(n_transactions=5000, n_customers=200):
    """Generate sample customer and transaction data."""

    today = datetime.now().date()
    one_year_ago = today - timedelta(days=365)

    # Generate customers
    customers = []
    for i in range(n_customers):
        # Signup dates: 6 months to 2 years ago
        signup_offset = random.randint(180, 730)
        customers.append({
            "customer_id": f"CUST-{i:04d}",
            "region": random.choice(REGIONS),
            "signup_date": (today - timedelta(days=signup_offset)).strftime("%Y-%m-%d"),
            "customer_segment": random.choices(SEGMENTS, weights=[30, 50, 20])[0],
        })

    with open("customers.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=customers[0].keys())
        writer.writeheader()
        writer.writerows(customers)

    # Generate transactions (last 12 months, with more recent months having more transactions)
    transactions = []
    base_prices = {
        "electronics": 150,
        "clothing": 50,
        "home": 40,
        "grocery": 25,
        "sports": 60
    }

    for i in range(n_transactions):
        cust = random.choice(customers)
        category = random.choice(CATEGORIES)
        base_price = base_prices[category]
        quantity = random.randint(1, 3)
        unit_price = round(base_price * random.uniform(0.5, 2.0), 2)

        # Weighted toward recent dates (more transactions in recent months)
        days_ago = int(random.triangular(0, 365, 60))
        txn_date = today - timedelta(days=days_ago)

        transactions.append({
            "transaction_id": f"TXN-{i:06d}",
            "customer_id": cust["customer_id"],
            "transaction_date": txn_date.strftime("%Y-%m-%d"),
            "category": category,
            "product_name": f"{category.title()} Item {random.randint(1, 20)}",
            "amount": round(unit_price * quantity, 2),
            "quantity": quantity,
            "payment_method": random.choice(["credit_card", "debit_card", "paypal", "apple_pay"]),
            "is_returned": random.random() < 0.08,
        })

    with open("transactions.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=transactions[0].keys())
        writer.writeheader()
        writer.writerows(transactions)

    print(f"✓ Generated {n_customers} customers -> customers.csv")
    print(f"✓ Generated {n_transactions} transactions -> transactions.csv")
    print(f"✓ Transaction dates: {one_year_ago} to {today}")


if __name__ == "__main__":
    generate_data()
