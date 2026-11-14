"""RiskLab 2.0 | SQLite demo database and introductory credit-risk SQL analysis.

Run: python3 database.py
All records are synthetic. No personal/customer data is stored.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
import random

DB_PATH = Path(__file__).with_name("risklab_demo.db")
AS_OF_DATE = date(2026, 11, 11)  # Fixed for reproducible demo results.

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    segment TEXT NOT NULL CHECK (segment IN ('Retail', 'SME', 'Corporate')),
    monthly_income REAL NOT NULL CHECK (monthly_income > 0)
);
CREATE TABLE IF NOT EXISTS loans (
    loan_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    outstanding_balance REAL NOT NULL CHECK (outstanding_balance >= 0),
    monthly_installment REAL NOT NULL CHECK (monthly_installment >= 0)
);
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY,
    loan_id INTEGER NOT NULL REFERENCES loans(loan_id),
    due_date TEXT NOT NULL,
    paid_date TEXT,
    amount_due REAL NOT NULL CHECK (amount_due >= 0),
    amount_paid REAL NOT NULL DEFAULT 0 CHECK (amount_paid >= 0),
    CHECK (amount_paid <= amount_due)
);
CREATE INDEX IF NOT EXISTS idx_loans_customer ON loans(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_loan_due ON payments(loan_id, due_date);
"""

# An overdue installment means due_date < as_of_date and unpaid balance > 0.
# Exposure at risk is counted ONCE per loan, even if it has multiple overdue payments.
OVERDUE_QUERY = """
WITH overdue_loans AS (
    SELECT DISTINCT loan_id
    FROM payments
    WHERE due_date >= date(:as_of_date, '-30 days')
      AND due_date < date(:as_of_date)
      AND amount_paid < amount_due
)
SELECT c.segment,
       COUNT(DISTINCT c.customer_id) AS affected_customers,
       COUNT(l.loan_id) AS overdue_loans,
       ROUND(SUM(l.outstanding_balance), 2) AS exposure_at_risk_tl
FROM overdue_loans o
JOIN loans l ON l.loan_id = o.loan_id
JOIN customers c ON c.customer_id = l.customer_id
GROUP BY c.segment
ORDER BY exposure_at_risk_tl DESC;
"""


def initialize_database(path: Path = DB_PATH, reset: bool = False) -> None:
    """Create tables and seed a reproducible, synthetic portfolio if empty."""
    if reset and path.exists():
        path.unlink()
    rng = random.Random(42)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]:
            return
        customers, loans, payments = [], [], []
        segments = ('Retail', 'SME', 'Corporate')
        for i in range(1, 101):
            segment = segments[(i - 1) % 3]
            income = rng.randint(25000, 150000)
            balance = rng.randint(30000, 500000)
            installment = rng.randint(2000, min(35000, income))
            customers.append((i, segment, income))
            loans.append((i, i, balance, installment))
            # One installment per loan, with due dates within the last 40 days.
            due = AS_OF_DATE - timedelta(days=rng.randint(1, 40))
            is_unpaid = rng.random() < 0.3
            paid = 0 if is_unpaid else installment
            paid_date = None if is_unpaid else (due + timedelta(days=rng.randint(0, 4))).isoformat()
            payments.append((i, i, due.isoformat(), paid_date, installment, paid))
        conn.executemany("INSERT INTO customers VALUES (?, ?, ?)", customers)
        conn.executemany("INSERT INTO loans VALUES (?, ?, ?, ?)", loans)
        conn.executemany("INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?)", payments)


def analyze_overdue(path: Path = DB_PATH, as_of_date: date = AS_OF_DATE) -> list[tuple]:
    """Return segment-level overdue counts and outstanding exposure."""
    with sqlite3.connect(path) as conn:
        return conn.execute(OVERDUE_QUERY, {"as_of_date": as_of_date.isoformat()}).fetchall()


PORTFOLIO_MONITORING_QUERY = """
-- Identify overdue loans once, even when several installments are overdue.
WITH overdue_loans AS (
    SELECT DISTINCT loan_id
    FROM payments
    WHERE due_date >= date(:as_of_date, '-30 days')
      AND due_date < date(:as_of_date)
      AND amount_paid < amount_due
),
segment_exposure AS (
    SELECT c.segment,
           COUNT(DISTINCT c.customer_id) AS total_customers,
           COUNT(l.loan_id) AS total_loans,
           SUM(l.outstanding_balance) AS total_exposure_tl,
           COUNT(o.loan_id) AS overdue_loans,
           COUNT(DISTINCT CASE WHEN o.loan_id IS NOT NULL THEN c.customer_id END)
               AS affected_customers,
           SUM(CASE WHEN o.loan_id IS NOT NULL
                    THEN l.outstanding_balance ELSE 0 END) AS overdue_exposure_tl
    FROM customers c
    JOIN loans l ON l.customer_id = c.customer_id
    LEFT JOIN overdue_loans o ON o.loan_id = l.loan_id
    GROUP BY c.segment
)
SELECT segment, total_customers, total_loans, overdue_loans,
       affected_customers,
       ROUND(total_exposure_tl, 2) AS total_exposure_tl,
       ROUND(overdue_exposure_tl, 2) AS overdue_exposure_tl,
       ROUND(100.0 * overdue_exposure_tl / NULLIF(total_exposure_tl, 0), 2)
           AS overdue_exposure_ratio_pct
FROM segment_exposure
ORDER BY overdue_exposure_ratio_pct DESC;
"""


def analyze_portfolio(path: Path = DB_PATH, as_of_date: date = AS_OF_DATE):
    """Return segment-level monitoring results as a pandas DataFrame."""
    import pandas as pd
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(
            PORTFOLIO_MONITORING_QUERY,
            conn,
            params={"as_of_date": as_of_date.isoformat()},
        )



# DPD is measured from the oldest installment still unpaid as of the reference date.
# This illustrative dataset has one installment per loan; the SQL also handles many.
DELINQUENCY_QUERY = """
WITH oldest_unpaid AS (
    SELECT loan_id, MIN(due_date) AS oldest_due_date
    FROM payments
    WHERE due_date < date(:as_of_date)
      AND amount_paid < amount_due
      AND (paid_date IS NULL OR paid_date > date(:as_of_date))
    GROUP BY loan_id
),
loan_dpd AS (
    SELECT l.loan_id, c.segment, l.outstanding_balance,
           CASE WHEN o.oldest_due_date IS NULL THEN 0
                ELSE CAST(julianday(:as_of_date) - julianday(o.oldest_due_date) AS INTEGER)
           END AS dpd
    FROM loans l
    JOIN customers c ON c.customer_id = l.customer_id
    LEFT JOIN oldest_unpaid o ON o.loan_id = l.loan_id
)
SELECT loan_id, segment, outstanding_balance, dpd,
       CASE WHEN dpd = 0 THEN 'Current'
            WHEN dpd < 30 THEN '1-29 DPD'
            WHEN dpd < 60 THEN '30-59 DPD'
            WHEN dpd < 90 THEN '60-89 DPD'
            ELSE '90+ DPD' END AS dpd_bucket
FROM loan_dpd
ORDER BY dpd DESC, loan_id;
"""


def analyze_delinquency(path: Path = DB_PATH, as_of_date: date = AS_OF_DATE):
    """One row per loan, with DPD and mutually exclusive delinquency bucket."""
    import pandas as pd
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(
            DELINQUENCY_QUERY, conn,
            params={"as_of_date": as_of_date.isoformat()},
        )

def save_portfolio_snapshot(
    path=DB_PATH,
    as_of_date=AS_OF_DATE
):
    """Save one historical portfolio snapshot per date."""

    snapshot = analyze_delinquency(path, as_of_date)

    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                snapshot_date TEXT NOT NULL,
                loan_id INTEGER NOT NULL,
                segment TEXT NOT NULL,
                outstanding_balance REAL NOT NULL,
                dpd INTEGER NOT NULL,
                dpd_bucket TEXT NOT NULL,
                PRIMARY KEY (snapshot_date, loan_id)
            )
        """)

        records = [
            (
                as_of_date.isoformat(),
                int(row.loan_id),
                row.segment,
                float(row.outstanding_balance),
                int(row.dpd),
                row.dpd_bucket
            )
            for row in snapshot.itertuples(index=False)
        ]

        conn.executemany("""
            INSERT OR IGNORE INTO portfolio_snapshots
            (snapshot_date, loan_id, segment,
             outstanding_balance, dpd, dpd_bucket)
            VALUES (?, ?, ?, ?, ?, ?)
        """, records)

    return len(records)


def simulate_next_month(
    db_path=DB_PATH,
    start_date="2026-11-11",
    end_date="2026-12-11"
):
    import sqlite3
    import random
    from datetime import date

    days_passed = (
        date.fromisoformat(end_date)
        - date.fromisoformat(start_date)
    ).days

    if days_passed <= 0:
        raise ValueError("End date must be after start date.")

    rng = random.Random(42)

    with sqlite3.connect(db_path) as conn:

        existing = conn.execute("""
            SELECT COUNT(*)
            FROM portfolio_snapshots
            WHERE snapshot_date = ?
        """, (end_date,)).fetchone()[0]

        if existing:
            print("Next-month snapshot already exists.")
            return

        loans = conn.execute("""
            SELECT loan_id, segment,
                   outstanding_balance, dpd
            FROM portfolio_snapshots
            WHERE snapshot_date = ?
            ORDER BY loan_id
        """, (start_date,)).fetchall()

        if not loans:
            raise ValueError("Starting snapshot not found.")

        records = []

        for loan_id, segment, balance, dpd in loans:

            outcome = rng.random()

            if outcome < 0.25:
                # Assumed full cure of overdue installments
                new_dpd = 0

            elif outcome < 0.40:
                # Partial improvement in overdue status
                new_dpd = max(0, dpd - 15)

            else:
                # No overdue installment cured
                if dpd > 0:
                    new_dpd = dpd + days_passed
                else:
                    # A previously current loan misses
                    # its next illustrative installment
                    new_dpd = days_passed

            if new_dpd == 0:
                bucket = "Current"
            elif new_dpd < 30:
                bucket = "1-29 DPD"
            elif new_dpd < 60:
                bucket = "30-59 DPD"
            elif new_dpd < 90:
                bucket = "60-89 DPD"
            else:
                bucket = "90+ DPD"

            records.append((
                end_date,
                loan_id,
                segment,
                balance,
                new_dpd,
                bucket
            ))

        conn.executemany("""
            INSERT INTO portfolio_snapshots (
                snapshot_date,
                loan_id,
                segment,
                outstanding_balance,
                dpd,
                dpd_bucket
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, records)

    print(
        f"Created {len(records)} simulated "
        f"loan records for {end_date}."
    )


def calculate_roll_rates(db_path=DB_PATH):
    import sqlite3
    import pandas as pd

    query = """
        SELECT
            a.dpd_bucket AS previous_bucket,
            b.dpd_bucket AS current_bucket,
            COUNT(*) AS loan_count
        FROM portfolio_snapshots a
        JOIN portfolio_snapshots b
            ON a.loan_id = b.loan_id
        WHERE a.snapshot_date = '2026-11-11'
          AND b.snapshot_date = '2026-12-11'
        GROUP BY a.dpd_bucket, b.dpd_bucket
    """

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn)

    bucket_order = [
        "Current",
        "1-29 DPD",
        "30-59 DPD",
        "60-89 DPD",
        "90+ DPD"
    ]

    matrix = df.pivot_table(
        index="previous_bucket",
        columns="current_bucket",
        values="loan_count",
        aggfunc="sum",
        fill_value=0
    )

    matrix = matrix.reindex(
        index=bucket_order,
        columns=bucket_order,
        fill_value=0
    )

    row_totals = matrix.sum(axis=1)

    roll_rates = (
        matrix.div(
            row_totals.replace(0, float("nan")),
            axis=0
        )
        .fillna(0)
        * 100
    )

    return matrix, roll_rates


if __name__ == "__main__":
    initialize_database()
    print(f"RiskLab synthetic SQL demo | As of {AS_OF_DATE.isoformat()}")
    print("Segment | Customers | Overdue loans | Exposure at risk (TL)")
    for segment, customers, loan_count, exposure in analyze_overdue():
        print(f"{segment:9} | {customers:9} | {loan_count:13} | {exposure:,.2f}")
    print("\nNote: Exposure at risk is NOT expected loss or probability of default.")

    print("\nPortfolio monitoring | last 30 days")
    print(analyze_portfolio().to_string(index=False))
