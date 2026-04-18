#!/usr/bin/env python3
"""
One-off import script: reads Feb 26, Mar 26, Apr 26 tabs from Google Sheets
and loads them into /root/.openclaw/db/tracker.db with correct run dates.

Run once manually:
  cd /root/.openclaw/workspace && source venv/bin/activate
  python import_sheets.py
"""

import sqlite3
import json
import re
from google.oauth2.service_account import Credentials
import gspread

CONFIG_FILE      = "/root/.openclaw/workspace/config.json"
CREDENTIALS_FILE = "/root/.openclaw/workspace/google-credentials.json"
DB_PATH          = "/root/.openclaw/db/tracker.db"

# Map sheet tab name -> ISO run date
SHEET_DATES = {
    "Feb 26": "2026-02-01",
    "Mar 26": "2026-03-01",
    "Apr 26": "2026-04-01",
}

# Column indices (0-based, matching your sheet layout)
# A=0  B=1  C=2  D=3  E=4  F=5  G=6  H=7  I=8  J=9  K=10 L=11 M=12 N=13 O=14
COL_ERA         = 0
COL_DATE        = 1
COL_NAME        = 2
COL_BB_PRICE    = 3
COL_SET_VALUE   = 4
COL_CHASE       = 5
COL_BOX_PCT     = 6
COL_REC         = 7
COL_CHASE_PCT   = 8
COL_PRINT       = 9
COL_DECISION    = 10
COL_SCARCITY    = 11
COL_LIQUIDITY   = 12
COL_MASCOT      = 13
COL_DEPTH       = 14

VALID_RECS = {"Strong Buy", "Buy", "Accumulate", "Hold", "Reduce", "Sell", "Overvalued"}


def connect_sheets():
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    gc = gspread.authorize(creds)
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    sh = gc.open_by_key(config["sheet_id"])
    return sh


def parse_float(val):
    """Safely parse a float from a cell value, handling %, £, commas."""
    if val is None or str(val).strip() == "":
        return None
    s = str(val).strip().replace("£", "").replace("$", "").replace(",", "").replace("%", "").strip()
    try:
        f = float(s)
        # If it was a percentage string (e.g. "24.7%"), convert to ratio
        if "%" in str(val):
            f = f / 100
        return f
    except ValueError:
        return None


def parse_int(val):
    """Safely parse an int from a cell value."""
    if val is None or str(val).strip() == "":
        return None
    try:
        return int(float(str(val).strip()))
    except ValueError:
        return None


def import_sheet(cur, ws, run_date, sheet_name):
    rows = ws.get_all_values()
    if not rows:
        print(f"  [{sheet_name}] Empty sheet, skipping")
        return 0, 0

    # Skip header row
    data_rows = rows[1:]
    sets_written = 0
    sets_scored  = 0
    skipped      = 0

    for i, row in enumerate(data_rows, start=2):
        # Pad row to 15 columns
        row = row + [""] * (15 - len(row))

        set_name = row[COL_NAME].strip()
        if not set_name:
            continue

        era          = row[COL_ERA].strip()
        date_rel     = row[COL_DATE].strip()
        print_status = row[COL_PRINT].strip()
        bb_price     = parse_float(row[COL_BB_PRICE])
        set_value    = parse_float(row[COL_SET_VALUE])
        chase        = row[COL_CHASE].strip() or None
        recommendation = row[COL_REC].strip()
        if recommendation not in VALID_RECS:
            recommendation = None

        # Box % — stored as ratio in DB
        box_pct_raw = row[COL_BOX_PCT].strip()
        box_pct = parse_float(box_pct_raw)
        if box_pct and box_pct > 1.0 and "%" not in box_pct_raw:
            # Already a ratio stored as e.g. 0.247 — keep as is
            pass
        elif box_pct and box_pct > 1.0:
            box_pct = box_pct / 100

        # Chase % — stored as ratio
        chase_pct_raw = row[COL_CHASE_PCT].strip()
        chase_pct = parse_float(chase_pct_raw)
        if chase_pct and chase_pct > 1.0:
            chase_pct = chase_pct / 100

        decision  = parse_int(row[COL_DECISION])
        scarcity  = parse_int(row[COL_SCARCITY])
        liquidity = parse_int(row[COL_LIQUIDITY])
        mascot    = parse_int(row[COL_MASCOT])
        depth     = parse_int(row[COL_DEPTH])

        # Upsert set metadata
        cur.execute("""
            INSERT INTO sets (name, era, date_released, print_status, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(name) DO UPDATE SET
                era           = CASE WHEN excluded.era != '' THEN excluded.era ELSE era END,
                date_released = CASE WHEN excluded.date_released != '' THEN excluded.date_released ELSE date_released END,
                print_status  = CASE WHEN excluded.print_status != '' THEN excluded.print_status ELSE print_status END,
                updated_at    = datetime('now')
        """, (set_name, era, date_rel, print_status))

        cur.execute("SELECT id FROM sets WHERE name = ?", (set_name,))
        row_result = cur.fetchone()
        if not row_result:
            skipped += 1
            continue
        set_id = row_result[0]

        # Upsert monthly snapshot
        cur.execute("""
            INSERT INTO monthly_snapshots
                (set_id, run_date, bb_price_gbp, set_value_gbp,
                 top3_chase, box_pct, chase_pct, price_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'sheets_import')
            ON CONFLICT(set_id, run_date) DO UPDATE SET
                bb_price_gbp  = excluded.bb_price_gbp,
                set_value_gbp = excluded.set_value_gbp,
                top3_chase    = excluded.top3_chase,
                box_pct       = excluded.box_pct,
                chase_pct     = excluded.chase_pct,
                price_source  = excluded.price_source
        """, (set_id, run_date, bb_price, set_value, chase, box_pct, chase_pct))
        sets_written += 1

        # Upsert score if we have meaningful data
        if any(v is not None for v in [scarcity, liquidity, mascot, depth, recommendation]):
            # Recalculate decision score from components if missing
            if decision is None and all(v is not None for v in [scarcity, liquidity, mascot, depth]):
                decision = scarcity + liquidity + mascot + depth

            cur.execute("""
                INSERT INTO scores
                    (set_id, run_date, recommendation, scarcity,
                     liquidity, mascot_power, set_depth, decision_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(set_id, run_date) DO UPDATE SET
                    recommendation = excluded.recommendation,
                    scarcity       = excluded.scarcity,
                    liquidity      = excluded.liquidity,
                    mascot_power   = excluded.mascot_power,
                    set_depth      = excluded.set_depth,
                    decision_score = excluded.decision_score
            """, (set_id, run_date, recommendation, scarcity, liquidity, mascot, depth, decision))
            sets_scored += 1

        print(f"    Row {i}: {set_name} | BB={bb_price} | Box%={box_pct} | Rec={recommendation} | Score={decision}")

    return sets_written, sets_scored


def main():
    print("=== Google Sheets -> SQLite Import ===\n")

    sh = connect_sheets()
    print(f"Connected to: {sh.title}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    total_sets    = 0
    total_scored  = 0

    available_sheets = [ws.title for ws in sh.worksheets()]
    print(f"Available tabs: {available_sheets}\n")

    for sheet_name, run_date in SHEET_DATES.items():
        if sheet_name not in available_sheets:
            print(f"[SKIP] Tab '{sheet_name}' not found in spreadsheet")
            continue

        print(f"[{sheet_name}] -> run_date={run_date}")
        ws = sh.worksheet(sheet_name)
        sets_written, sets_scored = import_sheet(cur, ws, run_date, sheet_name)

        # Log the import run
        cur.execute("""
            INSERT INTO run_log (run_date, sets_updated, sets_added, sets_scored, usd_gbp_rate, status, notes)
            VALUES (?, ?, 0, ?, 0.0, 'success', 'imported from Google Sheets')
            ON CONFLICT DO NOTHING
        """, (run_date, sets_written, sets_scored))

        total_sets   += sets_written
        total_scored += sets_scored
        print(f"  -> {sets_written} snapshots, {sets_scored} scores imported\n")

    conn.commit()
    conn.close()

    print("=" * 50)
    print(f"Import complete!")
    print(f"  Total snapshots : {total_sets}")
    print(f"  Total scores    : {total_scored}")
    print(f"\nVerify with:")
    print(f"  sqlite3 {DB_PATH} \"SELECT run_date, COUNT(*) FROM monthly_snapshots GROUP BY run_date;\"")


if __name__ == "__main__":
    main()
