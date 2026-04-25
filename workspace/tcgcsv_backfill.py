#!/usr/bin/env python3
"""
tcgcsv_backfill.py — Historical TCGCSV price backfill from 7z archives
Archive URL: https://tcgcsv.com/archive/tcgplayer/prices-{date}.ppmd.7z
Archive structure: {date}/{category_id}/{group_id}/prices  (no file extension, JSON content)

Idempotent: skips dates already in tcgcsv_prices.
Run overnight:
  nohup /root/.openclaw/workspace/venv/bin/python3 /root/.openclaw/workspace/tcgcsv_backfill.py     >> /root/.openclaw/logs/backfill.log 2>&1 &

Usage:
  python3 tcgcsv_backfill.py                               # full 2024-02-08 to today
  python3 tcgcsv_backfill.py --start 2025-01-06 --end 2025-01-12  # single week
  python3 tcgcsv_backfill.py --dry-run                     # show plan, no writes
"""

import sys
import json
import shutil
import logging
import tempfile
import argparse
from datetime import date, timedelta
from pathlib import Path
import time

import requests
import py7zr
import psycopg2
import psycopg2.extras

# ── Config ────────────────────────────────────────────────────────────────────
DATABASE_URL   = "host=localhost dbname=tcginvest user=tcginvest password=pxQSY8IjfYEsiBSd42e6ke+h4tmO1eFU705sLqYHJEU="
ARCHIVE_URL    = "https://tcgcsv.com/archive/tcgplayer/prices-{date}.ppmd.7z"
BACKFILL_START = date(2024, 2, 8)
CATEGORY_ID    = 3          # Pokemon TCG category on TCGplayer
LOG_FILE       = Path("/root/.openclaw/logs/backfill.log")
SLEEP_BETWEEN  = 1.5        # seconds between downloads (polite crawling)

HEADERS = {
    "User-Agent": "TCGInvest/1.0 (tcginvest.uk; historical-backfill; +https://tcginvest.uk)",
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


def load_tracked_group_ids(conn) -> set[int]:
    cur = conn.cursor()
    cur.execute("SELECT tcgcsv_group_ids FROM sets WHERE tcgcsv_group_ids IS NOT NULL")
    result = set()
    for (arr,) in cur.fetchall():
        if arr:
            result.update(arr)
    log.info(f"Loaded {len(result)} tracked group IDs from DB")
    return result


def get_ingested_dates(conn) -> set[date]:
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT snapshot_date FROM tcgcsv_prices")
    return {row[0] for row in cur.fetchall()}


def download_archive(target_date: date, dest: Path) -> bool:
    """Download archive to dest. Returns True on success, False if 404/error."""
    url = ARCHIVE_URL.format(date=target_date.isoformat())
    try:
        resp = requests.get(url, headers=HEADERS, timeout=120, stream=True)
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        return True
    except requests.RequestException as e:
        log.warning(f"  Download error: {e}")
        return False


def process_archive(archive_path: Path, target_date: date,
                    tracked_groups: set[int], ext_dir: Path) -> dict[int, list[dict]]:
    """
    Selectively extract only our tracked group files and parse them.
    Returns dict: group_id -> list of price dicts.
    """
    prefix = f"{target_date}/{CATEGORY_ID}/"
    results = {}

    with py7zr.SevenZipFile(archive_path, mode="r") as z:
        all_names = z.getnames()

        # Identify which files to extract
        targets = []
        name_to_gid = {}
        for name in all_names:
            if not name.startswith(prefix):
                continue
            parts = name.split("/")
            if len(parts) < 4:
                continue
            try:
                gid = int(parts[2])
            except ValueError:
                continue
            if gid in tracked_groups:
                targets.append(name)
                name_to_gid[name] = gid

        if not targets:
            return {}

        # Extract only the matched files
        ext_dir.mkdir(parents=True, exist_ok=True)
        z.extract(path=ext_dir, targets=targets)

    # Parse extracted files
    for f in ext_dir.rglob("*"):
        if not f.is_file():
            continue
        # Determine group_id from path
        gid = None
        for part in f.parts:
            try:
                candidate = int(part)
                if candidate in tracked_groups:
                    gid = candidate
                    break
            except ValueError:
                pass
        if gid is None:
            continue
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            rows = data.get("results", [])
            if isinstance(rows, list):
                results[gid] = rows
        except Exception as e:
            log.warning(f"    Parse error {f}: {e}")

    return results


def upsert_prices(cur, group_id: int, snapshot_date: date, price_rows: list[dict]) -> int:
    if not price_rows:
        return 0
    rows = []
    for p in price_rows:
        pid = p.get("productId")
        if pid is None:
            continue
        rows.append((
            int(pid),
            group_id,
            snapshot_date,
            p.get("marketPrice"),
            p.get("lowPrice"),
            p.get("midPrice"),
            p.get("subTypeName") or "Normal",
        ))
    if not rows:
        return 0
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO tcgcsv_prices
            (product_id, group_id, snapshot_date, market_price_usd,
             low_price_usd, mid_price_usd, sub_type_name)
        VALUES %s
        ON CONFLICT (product_id, sub_type_name, snapshot_date)
        DO UPDATE SET
            market_price_usd = EXCLUDED.market_price_usd,
            low_price_usd    = EXCLUDED.low_price_usd,
            mid_price_usd    = EXCLUDED.mid_price_usd,
            inserted_at      = NOW()
        """,
        rows, page_size=500,
    )
    return len(rows)


def run(start_date: date, end_date: date, dry_run: bool = False) -> None:
    log.info("=== tcgcsv_backfill.py starting ===")
    log.info(f"    Range:   {start_date} → {end_date}")
    log.info(f"    Dry run: {dry_run}")

    conn = psycopg2.connect(DATABASE_URL)
    tracked_groups = load_tracked_group_ids(conn)
    ingested_dates = get_ingested_dates(conn)

    all_dates = []
    d = start_date
    while d <= end_date:
        all_dates.append(d)
        d += timedelta(days=1)

    to_process = [d for d in all_dates if d not in ingested_dates]

    log.info(f"    Total dates:  {len(all_dates)}")
    log.info(f"    Already done: {len(all_dates) - len(to_process)}")
    log.info(f"    To process:   {len(to_process)}")

    if not to_process:
        log.info("Nothing to do.")
        conn.close()
        return

    if dry_run:
        sample = [str(d) for d in to_process[:5]]
        suffix = "..." if len(to_process) > 5 else ""
        log.info(f"DRY RUN — would process: {sample}{suffix}")
        conn.close()
        return

    total_rows = 0
    dates_ok = dates_skipped = dates_err = 0
    tmp_dir = Path(tempfile.mkdtemp(prefix="tcgcsv_"))
    log.info(f"    Temp dir: {tmp_dir}")

    try:
        for i, target_date in enumerate(to_process):
            archive_path = tmp_dir / f"{target_date}.7z"
            ext_dir      = tmp_dir / f"{target_date}_ext"

            try:
                log.info(f"[{i+1}/{len(to_process)}] {target_date} ...")

                # Download
                ok = download_archive(target_date, archive_path)
                if not ok:
                    log.debug(f"  {target_date}: no archive available")
                    dates_skipped += 1
                    time.sleep(SLEEP_BETWEEN)
                    continue

                size_kb = archive_path.stat().st_size // 1024
                log.debug(f"  Downloaded: {size_kb}KB")

                # Extract & parse
                group_data = process_archive(archive_path, target_date, tracked_groups, ext_dir)

                if not group_data:
                    log.debug(f"  {target_date}: no matching groups in archive")
                    dates_skipped += 1
                    continue

                # Upsert
                date_rows = 0
                with conn.cursor() as cur:
                    for gid, prices in group_data.items():
                        count = upsert_prices(cur, gid, target_date, prices)
                        date_rows += count
                conn.commit()

                total_rows += date_rows
                dates_ok   += 1
                log.info(f"  ✓ {date_rows:,} rows | {len(group_data)} groups (running: {total_rows:,})")

            except Exception as e:
                conn.rollback()
                dates_err += 1
                log.error(f"  ✗ {target_date} FAILED: {e}", exc_info=True)

            finally:
                archive_path.unlink(missing_ok=True)
                shutil.rmtree(ext_dir, ignore_errors=True)

            time.sleep(SLEEP_BETWEEN)

    finally:
        conn.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    log.info("=== Backfill complete ===")
    log.info(f"    ok={dates_ok}  skipped={dates_skipped}  errors={dates_err}")
    log.info(f"    total_rows={total_rows:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TCGCSV historical price backfill")
    parser.add_argument("--start", default=BACKFILL_START.isoformat())
    parser.add_argument("--end",   default=date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end   = date.fromisoformat(args.end)
    if start > end:
        print(f"Error: start ({start}) > end ({end})")
        sys.exit(1)

    run(start_date=start, end_date=end, dry_run=args.dry_run)
