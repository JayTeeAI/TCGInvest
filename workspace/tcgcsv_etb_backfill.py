#!/usr/bin/env python3
"""
tcgcsv_etb_backfill.py — Backfill etb_price_snapshots from tcgcsv_prices
For each ETB with a tcgcsv_product_id, inserts one snapshot per week
(using the Monday of each week) for dates where no eBay snapshot exists.
Price source flagged as 'tcgcsv'. USD converted to GBP via monthly FX table.

Run once after the main tcgcsv backfill completes.
"""
from datetime import date, timedelta
import psycopg2
import psycopg2.extras

DATABASE_URL = "host=localhost dbname=tcginvest user=tcginvest password=pxQSY8IjfYEsiBSd42e6ke+h4tmO1eFU705sLqYHJEU="

# Monthly USD/GBP averages
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

def monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())

def get_week_mondays(start: date, end: date):
    """Yield the Monday of each week in range."""
    d = monday_of_week(start)
    while d <= end:
        yield d
        d += timedelta(weeks=1)

def run():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Load ETBs with TCGCSV product IDs
    cur.execute("""
        SELECT id, name, tcgcsv_product_id
        FROM etbs
        WHERE tcgcsv_product_id IS NOT NULL
        ORDER BY id
    """)
    etbs = cur.fetchall()
    print(f"ETBs with tcgcsv_product_id: {len(etbs)}")

    # Load existing snapshot dates per ETB to avoid duplicates
    cur.execute("SELECT etb_id, snapshot_date FROM etb_price_snapshots")
    existing = {(r['etb_id'], r['snapshot_date']) for r in cur.fetchall()}
    print(f"Existing etb_price_snapshots rows: {len(existing)}")

    inserted = 0
    skipped_exists = 0
    skipped_no_price = 0

    today = date.today()
    backfill_start = date(2024, 2, 8)  # First available archive date

    for etb in etbs:
        etb_id = etb['id']
        pid = etb['tcgcsv_product_id']

        for monday in get_week_mondays(backfill_start, today):
            if (etb_id, monday) in existing:
                skipped_exists += 1
                continue

            # Find best price in the 7-day window starting on Monday
            week_end = monday + timedelta(days=6)

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
            """, (pid, monday, week_end))
            price_row = cur.fetchone()

            if not price_row:
                skipped_no_price += 1
                continue

            usd_price = float(price_row['market_price_usd'])
            fx = FX_RATES.get((monday.year, monday.month), 0.785)
            gbp_price = round(usd_price * fx, 2)

            cur.execute("""
                INSERT INTO etb_price_snapshots
                    (etb_id, snapshot_date, ebay_avg_sold_gbp, usd_gbp_rate, price_source)
                VALUES (%s, %s, %s, %s, 'tcgcsv')
                ON CONFLICT DO NOTHING
            """, (etb_id, monday, gbp_price, fx))

            inserted += 1

    conn.commit()
    conn.close()

    print(f"Inserted:           {inserted}")
    print(f"Skipped (exists):   {skipped_exists}")
    print(f"Skipped (no price): {skipped_no_price}")

if __name__ == "__main__":
    run()
