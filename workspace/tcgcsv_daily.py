#!/usr/bin/env python3
"""
tcgcsv_daily.py — Daily TCGCSV price ingestion pipeline
Fetches all Pokemon TCG groups from TCGCSV, iterates products + prices,
upserts into tcgcsv_prices table.

Schedule: 0 21 * * * (runs 1hr after TCGCSV updates at 20:00 UTC)
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime, timezone, date
from pathlib import Path

import psycopg2
import psycopg2.extras

# ── Config ────────────────────────────────────────────────────────────────────
DATABASE_URL    = "host=localhost dbname=tcginvest user=tcginvest password=pxQSY8IjfYEsiBSd42e6ke+h4tmO1eFU705sLqYHJEU="
CATEGORY_ID     = 3          # Pokemon TCG on TCGplayer
BASE_URL        = "https://tcgcsv.com/tcgplayer"
LAST_UPDATED_URL = "https://tcgcsv.com/last-updated.txt"
STATE_FILE      = Path(__file__).parent / "state" / "tcgcsv_last_ingested.txt"
LOG_FILE        = Path("/root/.openclaw/logs/tcgcsv_daily.log")
SLEEP_BETWEEN   = 0.1        # 100ms between group requests
DRY_RUN_LIMIT   = None       # Set to 3 for dry-run testing

HEADERS = {
    "User-Agent": "TCGInvest/1.0 (tcginvest.uk; price-tracker; +https://tcginvest.uk)",
    "Accept": "application/json",
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def get_last_updated_remote() -> str:
    """Fetch the TCGCSV last-updated timestamp string."""
    resp = requests.get(LAST_UPDATED_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.text.strip()


def get_last_ingested_local() -> str:
    """Read the local state file; return empty string if missing."""
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    return ""


def write_last_ingested(ts: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(ts)


def already_ingested_today() -> bool:
    """Return True if we already ran a successful ingest for today's date."""
    local_ts = get_last_ingested_local()
    if not local_ts:
        return False
    try:
        local_date = datetime.fromisoformat(local_ts.replace("Z", "+00:00")).date()
        return local_date == date.today()
    except ValueError:
        return False


def fetch_groups() -> list[dict]:
    """Fetch all Pokemon TCG groups from TCGCSV."""
    url = f"{BASE_URL}/{CATEGORY_ID}/groups"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    groups = data.get("results", [])
    log.info(f"Fetched {len(groups)} groups for categoryId={CATEGORY_ID}")
    return groups


def fetch_products(group_id: int) -> dict[int, dict]:
    """Fetch products for a group; returns dict keyed by productId."""
    url = f"{BASE_URL}/{CATEGORY_ID}/{group_id}/products"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    data = resp.json()
    return {p["productId"]: p for p in data.get("results", [])}


def fetch_prices(group_id: int) -> list[dict]:
    """Fetch price rows for a group."""
    url = f"{BASE_URL}/{CATEGORY_ID}/{group_id}/prices"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def upsert_prices(cur, group_id: int, today: date, price_rows: list[dict]) -> int:
    """Upsert price rows into tcgcsv_prices. Returns count of upserted rows."""
    if not price_rows:
        return 0

    rows = [
        (
            p["productId"],
            group_id,
            today,
            p.get("marketPrice"),
            p.get("lowPrice"),
            p.get("midPrice"),
            p.get("subTypeName") or "Normal",
        )
        for p in price_rows
        if p.get("productId") is not None
    ]

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO tcgcsv_prices
            (product_id, group_id, snapshot_date, market_price_usd, low_price_usd, mid_price_usd, sub_type_name)
        VALUES %s
        ON CONFLICT (product_id, sub_type_name, snapshot_date)
        DO UPDATE SET
            market_price_usd = EXCLUDED.market_price_usd,
            low_price_usd    = EXCLUDED.low_price_usd,
            mid_price_usd    = EXCLUDED.mid_price_usd,
            inserted_at      = NOW()
        """,
        rows,
        page_size=500,
    )
    return len(rows)


def run(dry_run_limit: int = None) -> None:
    today = date.today()
    log.info(f"=== tcgcsv_daily.py starting | date={today} dry_run_limit={dry_run_limit} ===")

    # ── Check if already ingested today ──────────────────────────────────────
    if dry_run_limit is None and already_ingested_today():
        local_ts = get_last_ingested_local()
        log.info(f"Already ingested today ({local_ts}). Skipping.")
        return

    # ── Fetch remote last-updated ─────────────────────────────────────────────
    try:
        remote_ts = get_last_updated_remote()
        log.info(f"TCGCSV last-updated: {remote_ts}")
    except Exception as e:
        log.error(f"Failed to fetch last-updated.txt: {e}")
        remote_ts = datetime.now(timezone.utc).isoformat()

    # ── Fetch groups ──────────────────────────────────────────────────────────
    groups = fetch_groups()
    if dry_run_limit:
        groups = groups[:dry_run_limit]
        log.info(f"DRY RUN: limited to {dry_run_limit} groups")

    # ── Connect to DB ─────────────────────────────────────────────────────────
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    total_rows = 0
    groups_ok = 0
    groups_err = 0

    try:
        for i, group in enumerate(groups):
            gid  = group["groupId"]
            name = group["name"]
            try:
                prices = fetch_prices(gid)
                if not prices:
                    log.debug(f"  [{i+1}/{len(groups)}] {name} (id={gid}) — no prices, skipping")
                    time.sleep(SLEEP_BETWEEN)
                    continue

                with conn.cursor() as cur:
                    count = upsert_prices(cur, gid, today, prices)
                conn.commit()

                total_rows += count
                groups_ok  += 1
                log.info(f"  [{i+1}/{len(groups)}] {name} (id={gid}) — {count} rows upserted")

            except Exception as e:
                conn.rollback()
                groups_err += 1
                log.error(f"  [{i+1}/{len(groups)}] {name} (id={gid}) — ERROR: {e}")

            time.sleep(SLEEP_BETWEEN)

    finally:
        conn.close()

    log.info(f"=== Done | groups_ok={groups_ok} groups_err={groups_err} total_rows={total_rows} ===")

    # ── Write state (only on full runs without errors) ────────────────────────
    if dry_run_limit is None and groups_err == 0:
        write_last_ingested(remote_ts)
        log.info(f"State written: {remote_ts}")
    elif dry_run_limit:
        log.info("DRY RUN complete — state file NOT updated")


if __name__ == "__main__":
    limit = DRY_RUN_LIMIT
    if "--dry-run" in sys.argv:
        try:
            idx = sys.argv.index("--dry-run")
            limit = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 3
        except (ValueError, IndexError):
            limit = 3
    run(dry_run_limit=limit)
