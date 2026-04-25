#!/usr/bin/env python3
"""
tcgcsv_bb_backfill.py — Backfill monthly_snapshots from tcgcsv_prices
For each set with a tcgcsv_bb_product_id, for each calendar month from
Feb 2024 to today, takes the first available price row and converts
USD → GBP using historical monthly FX averages.

Only inserts months not already present in monthly_snapshots.
Marks rows as price_source = 'tcgcsv_backfill'.

Run once after the main tcgcsv backfill completes.
"""
import sys
from datetime import date, timedelta
from decimal import Decimal
import psycopg2
import psycopg2.extras

DATABASE_URL = "host=localhost dbname=tcginvest user=tcginvest password=pxQSY8IjfYEsiBSd42e6ke+h4tmO1eFU705sLqYHJEU="

# Monthly USD/GBP averages (approximate mid-market rates)
# Source: historical averages 2024-2026
FX_RATES = {
    (2024,  1): 0.787, (2024,  2): 0.793, (2024,  3): 0.792,
    (2024,  4): 0.796, (2024,  5): 0.794, (2024,  6): 0.786,
    (2024,  7): 0.779, (2024,  8): 0.778, (2024,  9): 0.769,
    (2024, 10): 0.771, (2024, 11): 0.786, (2024, 12): 0.795,
    (2025,  1): 0.812, (2025,  2): 0.800, (2025,  3): 0.774,
    (2025,  4): 0.773, (2025,  5): 0.756, (2025,  6): 0.752,
    (2025,  7): 0.767, (2025,  8): 0.762, (2025,  9): 0.757,
    (2025, 10): 0.768, (2025, 11): 0.779, (2025, 12): 0.792,
    (2026,  1): 0.799, (2026,  2): 0.795, (2026,  3): 0.771,
    (2026,  4): 0.765,
}

def get_month_starts(start: date, end: date):
    """Yield the first day of each month in range."""
    d = start.replace(day=1)
    while d <= end:
        yield d
        # Next month
        if d.month == 12:
            d = d.replace(year=d.year + 1, month=1)
        else:
            d = d.replace(month=d.month + 1)

def run():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Load all sets with a BB product ID
    cur.execute("""
        SELECT id, name, tcgcsv_bb_product_id
        FROM sets
        WHERE tcgcsv_bb_product_id IS NOT NULL
        ORDER BY id
    """)
    sets = cur.fetchall()
    print(f"Sets with BB product ID: {len(sets)}")

    # Load existing monthly_snapshots to skip duplicates
    cur.execute("SELECT set_id, run_date FROM monthly_snapshots")
    existing = {(r['set_id'], r['run_date']) for r in cur.fetchall()}
    print(f"Existing monthly_snapshots rows: {len(existing)}")

    inserted = 0
    skipped_exists = 0
    skipped_no_price = 0

    today = date.today()
    backfill_start = date(2024, 2, 1)

    for s in sets:
        set_id = s['id']
        pid = s['tcgcsv_bb_product_id']

        for month_start in get_month_starts(backfill_start, today):
            if (set_id, month_start) in existing:
                skipped_exists += 1
                continue

            # Find first available price in this month for this product
            month_end = date(
                month_start.year + (1 if month_start.month == 12 else 0),
                1 if month_start.month == 12 else month_start.month + 1,
                1
            ) - timedelta(days=1)

            cur.execute("""
                SELECT snapshot_date, market_price_usd
                FROM tcgcsv_prices
                WHERE product_id = %s
                  AND snapshot_date >= %s
                  AND snapshot_date <= %s
                  AND market_price_usd IS NOT NULL
                  AND sub_type_name = 'Normal'
                ORDER BY snapshot_date ASC
                LIMIT 1
            """, (pid, month_start, month_end))
            price_row = cur.fetchone()

            if not price_row:
                skipped_no_price += 1
                continue

            usd_price = float(price_row['market_price_usd'])
            fx = FX_RATES.get((month_start.year, month_start.month), 0.785)
            gbp_price = round(usd_price * fx, 2)

            cur.execute("""
                INSERT INTO monthly_snapshots
                    (set_id, run_date, bb_price_gbp, price_source)
                VALUES (%s, %s, %s, 'tcgcsv_backfill')
                ON CONFLICT DO NOTHING
            """, (set_id, month_start, gbp_price))

            inserted += 1

    conn.commit()
    conn.close()

    print(f"Inserted:          {inserted}")
    print(f"Skipped (exists):  {skipped_exists}")
    print(f"Skipped (no price):{skipped_no_price}")

if __name__ == "__main__":
    run()
