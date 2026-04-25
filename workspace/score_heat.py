#!/usr/bin/env python3
"""
score_heat.py — Set Heat Score daily computation
Sprint 4 Batch 6

Composite heat score (0-100) per set:
  40% bb_trend_score    — 30-day BB price momentum (tcgcsv_prices)
  35% chase_trend_score — avg 30-day change of top-3 chase cards (chase_card_prices)
  25% pull_rate_score   — static quality proxy (decision_score normalised; swap for pull rates when seeded)

Runs daily at 22:00 (1hr after ingest at 21:00).
"""

import psycopg2
import psycopg2.extras
from datetime import date, timedelta
import sys
import logging

logging.basicConfig(
    filename="/root/.openclaw/logs/score_heat.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

DB_PARAMS = dict(
    host="localhost", dbname="tcginvest",
    user="tcginvest", password="pxQSY8IjfYEsiBSd42e6ke+h4tmO1eFU705sLqYHJEU="
)

WEIGHTS = dict(bb=0.40, chase=0.35, pull=0.25)
TODAY = date.today()
THIRTY_AGO = TODAY - timedelta(days=30)


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def normalise(values: dict) -> dict:
    """Min-max normalise a dict of {key: raw_value} -> {key: 0-100}"""
    valid = {k: v for k, v in values.items() if v is not None}
    if not valid:
        return {k: 50.0 for k in values}
    lo, hi = min(valid.values()), max(valid.values())
    if hi == lo:
        return {k: (50.0 if v is not None else 50.0) for k, v in values.items()}
    return {
        k: (clamp((v - lo) / (hi - lo) * 100) if v is not None else 50.0)
        for k, v in values.items()
    }


def compute_bb_trends(cur) -> dict:
    """
    For each set with a tcgcsv_bb_product_id, compute pct change of
    market_price_usd over the last 30 days.
    Uses sub_type_name='Normal' to match the booster box product (same as /api/movers/daily).
    Returns {set_id: pct_change_or_None}
    """
    cur.execute("""
        SELECT s.id AS set_id, s.tcgcsv_bb_product_id
        FROM sets s
        WHERE s.tcgcsv_bb_product_id IS NOT NULL
    """)
    rows = cur.fetchall()

    trends = {}
    for row in rows:
        set_id = row["set_id"]
        product_id = row["tcgcsv_bb_product_id"]

        # Latest price (most recent snapshot)
        cur.execute("""
            SELECT market_price_usd FROM tcgcsv_prices
            WHERE product_id = %s AND sub_type_name = 'Normal'
              AND snapshot_date >= %s AND market_price_usd IS NOT NULL
            ORDER BY snapshot_date DESC LIMIT 1
        """, (product_id, TODAY - timedelta(days=7)))
        latest = cur.fetchone()

        # Price ~30 days ago (within 7-day window around THIRTY_AGO)
        cur.execute("""
            SELECT market_price_usd FROM tcgcsv_prices
            WHERE product_id = %s AND sub_type_name = 'Normal'
              AND snapshot_date BETWEEN %s AND %s AND market_price_usd IS NOT NULL
            ORDER BY snapshot_date ASC LIMIT 1
        """, (product_id, THIRTY_AGO - timedelta(days=3), THIRTY_AGO + timedelta(days=3)))
        prev = cur.fetchone()

        if latest and prev and prev["market_price_usd"] and float(prev["market_price_usd"]) > 0:
            pct = (float(latest["market_price_usd"]) - float(prev["market_price_usd"])) / float(prev["market_price_usd"]) * 100
            trends[set_id] = pct
        else:
            trends[set_id] = None

    return trends


def compute_chase_trends(cur) -> dict:
    """
    For each set, compute avg 30-day pct change of top-3 chase cards by raw_gbp.
    Returns {set_id: avg_pct_change_or_None}
    """
    # Get all sets
    cur.execute("SELECT id FROM sets")
    all_sets = [r["id"] for r in cur.fetchall()]

    trends = {}
    for set_id in all_sets:
        # Get top-3 active chase cards for this set (by latest raw_gbp)
        cur.execute("""
            SELECT cc.id FROM chase_cards cc
            JOIN (
                SELECT chase_card_id, MAX(raw_gbp) as max_price
                FROM chase_card_prices
                GROUP BY chase_card_id
            ) p ON p.chase_card_id = cc.id
            WHERE cc.set_id = %s AND cc.active = TRUE
            ORDER BY p.max_price DESC NULLS LAST
            LIMIT 3
        """, (set_id,))
        card_ids = [r["id"] for r in cur.fetchall()]

        if not card_ids:
            trends[set_id] = None
            continue

        pcts = []
        for card_id in card_ids:
            cur.execute("""
                SELECT raw_gbp FROM chase_card_prices
                WHERE chase_card_id = %s
                ORDER BY snapshot_date DESC LIMIT 1
            """, (card_id,))
            latest = cur.fetchone()

            cur.execute("""
                SELECT raw_gbp FROM chase_card_prices
                WHERE chase_card_id = %s
                  AND snapshot_date BETWEEN %s AND %s
                ORDER BY snapshot_date ASC LIMIT 1
            """, (card_id, THIRTY_AGO - timedelta(days=7), THIRTY_AGO + timedelta(days=7)))
            old = cur.fetchone()

            if latest and old and old["raw_gbp"] and float(old["raw_gbp"]) > 0:
                pct = (float(latest["raw_gbp"]) - float(old["raw_gbp"])) / float(old["raw_gbp"]) * 100
                pcts.append(pct)

        trends[set_id] = sum(pcts) / len(pcts) if pcts else None

    return trends


def compute_pull_rate_scores(cur) -> dict:
    """
    Proxy: normalise decision_score (0-20) to 0-100 via scores table.
    TODO: replace with actual pull_rate_per_box from chase_cards when seeded.
    """
    cur.execute("""
        SELECT DISTINCT ON (set_id) set_id, decision_score
        FROM scores
        ORDER BY set_id, created_at DESC NULLS LAST
    """)
    rows = cur.fetchall()
    raw = {r["set_id"]: (float(r["decision_score"]) / 20.0 * 100 if r["decision_score"] is not None else None)
           for r in rows}
    return raw


def run():
    conn = psycopg2.connect(**DB_PARAMS, cursor_factory=psycopg2.extras.RealDictCursor)
    cur = conn.cursor()

    log.info("Starting heat score computation for %s", TODAY)

    bb_raw = compute_bb_trends(cur)
    chase_raw = compute_chase_trends(cur)
    pull_raw = compute_pull_rate_scores(cur)

    # Get all set IDs
    cur.execute("SELECT id FROM sets")
    all_set_ids = [r["id"] for r in cur.fetchall()]

    # Ensure all sets present in each dict (default None = neutral 50)
    for sid in all_set_ids:
        bb_raw.setdefault(sid, None)
        chase_raw.setdefault(sid, None)
        pull_raw.setdefault(sid, None)

    # Normalise each component across all sets
    bb_norm = normalise(bb_raw)
    chase_norm = normalise(chase_raw)
    # pull_raw is already 0-100 (decision_score proxy), but normalise for consistency
    pull_norm = normalise(pull_raw)

    inserted = 0
    for sid in all_set_ids:
        bb_s = bb_norm[sid]
        ch_s = chase_norm[sid]
        pr_s = pull_norm[sid]
        composite = clamp(
            bb_s * WEIGHTS["bb"] + ch_s * WEIGHTS["chase"] + pr_s * WEIGHTS["pull"]
        )

        cur.execute("""
            INSERT INTO set_heat_scores (set_id, score_date, heat_score, bb_trend_score, chase_trend_score, pull_rate_score)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (set_id, score_date) DO UPDATE SET
                heat_score = EXCLUDED.heat_score,
                bb_trend_score = EXCLUDED.bb_trend_score,
                chase_trend_score = EXCLUDED.chase_trend_score,
                pull_rate_score = EXCLUDED.pull_rate_score
        """, (sid, TODAY, round(composite, 2), round(bb_s, 2), round(ch_s, 2), round(pr_s, 2)))
        inserted += 1

    conn.commit()
    log.info("Upserted %d heat scores for %s", inserted, TODAY)
    print(f"Done: {inserted} heat scores computed for {TODAY}")
    conn.close()


if __name__ == "__main__":
    run()
