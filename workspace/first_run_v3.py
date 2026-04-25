#!/usr/bin/env python3
"""
Pokemon Booster Box Tracker — v3 Monthly Updater
Changes from v2:
- Set value combines base set + sub-sets (Trainer Gallery, Shiny Vault etc.)
- Era always stored as short ALL CAPS code with mapping table
- One-time Era backfill on every run
- Column G displayed as percentage, Column I as ratio 0.00
- Conditional formatting: light colours + coloured text
- Only touches columns B, G, I, K — never overwrites user row colours
- Groq scoring replaces Gemini, force re-score with revised rubric
- Backup fixed using fresh credentials refresh
- SQLite writer added: writes to /root/.openclaw/db/tracker.db on every run
"""

import re
import os
import json
import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
load_dotenv("/root/.openclaw/api/.env")
from dotenv import load_dotenv
load_dotenv("/root/.openclaw/api/.env")
import shutil
import time
import datetime
from datetime import date
import requests
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
import gspread
from google.oauth2.service_account import Credentials

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE      = "/root/.openclaw/workspace/config.json"
CREDENTIALS_FILE = "/root/.openclaw/workspace/google-credentials.json"
BACKUP_DIR       = "/root/.openclaw/workspace/backups"
DB_PATH          = "/root/.openclaw/db/tracker.db"
DATABASE_URL     = os.getenv("DATABASE_URL", "")
WIZARD_BASE      = "https://www.pokemonwizard.com"
HEADERS          = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
PROTECTED_SHEETS = {"Selling Individual Cards"}
NEW_SET_DAYS     = 60
GROQ_URL         = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL       = "llama-3.3-70b-versatile"

# Column indices (1-based for gspread)
COL = {
    "era": 1, "date": 2, "name": 3, "bb_price": 4, "set_value": 5,
    "chase": 6, "box_pct": 7, "recommendation": 8, "chase_pct": 9,
    "print_status": 10, "decision": 11, "scarcity": 12,
    "liquidity": 13, "mascot": 14, "depth": 15
}

# ── Era mapping ───────────────────────────────────────────────────────────────
ERA_MAP = {
    "scarlet & violet": "S&V",
    "scarlet and violet": "S&V",
    "sword & shield": "SWSH",
    "sword and shield": "SWSH",
    "mega evolution": "MEGA",
    "sun & moon": "SM",
    "sun and moon": "SM",
    "xy": "XY",
    "black & white": "BW",
    "black and white": "BW",
    "ex": "EX",
    "home": "MEGA",
}

VALID_ERA_CODES = {"S&V", "SWSH", "MEGA", "SM", "XY", "BW", "EX"}

def normalise_era(raw_era):
    if not raw_era:
        return ""
    key = raw_era.strip().lower()
    if key in ERA_MAP:
        return ERA_MAP[key]
    if raw_era.strip().upper() in VALID_ERA_CODES:
        return raw_era.strip().upper()
    for k, v in ERA_MAP.items():
        if k in key:
            return v
    return raw_era.strip().upper()[:6]

# ── Sub-set mapping ───────────────────────────────────────────────────────────
SUBSET_MAP = {
    "brilliant stars":   ["brilliant stars trainer gallery"],
    "silver tempest":    ["silver tempest: trainer gallery"],
    "lost origin":       ["lost origin: trainer gallery"],
    "astral radiance":   ["astral radiance trainer gallery"],
    "crown zenith":      ["crown zenith: galarian gallery"],
    "celebrations 25th": ["celebrations: classic collection"],
    "hidden fates":      ["hidden fates: shiny vault"],
    "shining fates":     ["shining fates: shiny vault"],
}

# ── Name mappings ─────────────────────────────────────────────────────────────
DAWNGLARE_MAP = {
    "ascended hereos":             "ascended heroes",
    "celebrations 25th":           "celebrations",
    "champions path":              "champion's path",
    "s&v base set":                "scarlet & violet",
    "mega evolution (enhanced)":   "mega evolution enhanced",
    "journey together (enhanced)": "journey together enhanced",
    "evolutions":                  "xy evolutions",
    "sword and shield":            "sword & shield",
}

ETB_ONLY_SETS = {
    "prismatic evolutions":  "prismatic evolutions elite trainer box",
    "black bolt":            "black bolt elite trainer box",
    "white flare":           "white flare elite trainer box",
    "ascended hereos":       "ascended heroes elite trainer box",
    "celebrations 25th":     "celebrations elite trainer box",
    "champions path":        "champion's path elite trainer box",
    "shining fates":         "shining fates elite trainer box",
    "crown zenith":          "crown zenith elite trainer box",
    "paldean fates":         "paldean fates elite trainer box",
    "151":                   "151 elite trainer box",
    "hidden fates":          "hidden fates elite trainer box",
    "shrouded fable":        "shrouded fable elite trainer box",
}

WIZARD_NAME_MAP = {
    "s&v base set":                "Scarlet & Violet Base Set",
    "151":                         "Scarlet & Violet 151",
    "ascended hereos":             "Ascended Heroes",
    "celebrations 25th":           "Celebrations",
    "champions path":              "Champion's Path",
    "sword and shield":            "Sword & Shield",
    "mega evolution (enhanced)":   "Mega Evolution",
    "journey together (enhanced)": "Journey Together",
}

VALID_RECOMMENDATIONS = {"Strong Buy", "Buy", "Accumulate", "Hold", "Overvalued"}

# ── Google Sheets connection ──────────────────────────────────────────────────
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
    return sh, config

def get_fresh_token():
    import google.auth.transport.requests
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    req = google.auth.transport.requests.Request()
    creds.refresh(req)
    return creds.token

# ── Backup ────────────────────────────────────────────────────────────────────
def backup_sheet(sh):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    today_str = date.today().strftime("%Y-%m-%d")
    backup_path = os.path.join(BACKUP_DIR, f"pokemon-tracker-backup-{today_str}.xlsx")
    try:
        token = get_fresh_token()
        url = f"https://docs.google.com/spreadsheets/d/{sh.id}/export?format=xlsx"
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        with open(backup_path, "wb") as f:
            f.write(r.content)
        print(f"  Backup saved: {backup_path}")
    except Exception as e:
        print(f"  [WARN] Backup failed: {e}")
        return

    backups = sorted([
        os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)
        if f.startswith("pokemon-tracker-backup-")
    ])
    for old in backups[:-3]:
        os.remove(old)
        print(f"  Removed old backup: {old}")

# ── Sheet management ──────────────────────────────────────────────────────────
def sheet_name_for(dt=None):
    return (dt or date.today()).strftime("%b %y")

def prev_sheet_name(dt=None):
    dt = dt or date.today()
    prev = dt.replace(day=1) - datetime.timedelta(days=1)
    return prev.strftime("%b %y")

def get_or_create_monthly_sheet(sh):
    new_name = sheet_name_for()
    prev_name = prev_sheet_name()
    existing = [ws.title for ws in sh.worksheets()]

    if new_name in existing:
        print(f"  Sheet '{new_name}' already exists — updating in place.")
        ws = sh.worksheet(new_name)
    else:
        src_name = prev_name if prev_name in existing else next(
            t for t in existing if t not in PROTECTED_SHEETS
        )
        src = sh.worksheet(src_name)
        ws = src.duplicate(insert_sheet_index=0, new_sheet_name=new_name)
        print(f"  Created sheet '{new_name}' from '{src_name}'")

    all_sheets = sh.worksheets()
    sh.reorder_worksheets([ws] + [w for w in all_sheets if w.title != new_name])
    print(f"  Sheet '{new_name}' is at position 0")

    ensure_headers(ws, sh)
    return ws

def ensure_headers(ws, sh):
    headers = [
        "Era", "Date Released", "Set Name", "BB Price (GBP)", "Set Value (GBP)",
        "Top 3 Chase Cards", "Box %", "Recommendation", "Chase Card %",
        "Print Status", "Decision Score", "Scarcity", "Liquidity",
        "Mascot Power", "Set Depth"
    ]
    current = ws.row_values(1)
    if current != headers:
        ws.update(range_name="A1:O1", values=[headers])
        print("  Headers written to row 1")

    try:
        sh.batch_update({"requests": [
            {
                "repeatCell": {
                    "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {"userEnteredFormat": {
                        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.6},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
                    }},
                    "fields": "userEnteredFormat"
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
                    "fields": "gridProperties.frozenRowCount"
                }
            },
            {
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": ws.id,
                            "startRowIndex": 0,
                            "startColumnIndex": 0,
                            "endColumnIndex": 15
                        }
                    }
                }
            }
        ]})
        print("  Headers styled, frozen and filtered")
    except Exception as e:
        print(f"  [WARN] Header formatting failed: {e}")

# ── Era backfill ──────────────────────────────────────────────────────────────
def backfill_era(ws, sh, wizard_index):
    all_rows = ws.get_all_values()
    updates = []

    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) < 3 or not row[2].strip():
            continue
        current_era = row[0].strip() if row else ""
        set_name = row[2].strip()

        needs_fix = (
            not current_era or
            current_era not in VALID_ERA_CODES or
            current_era.lower() in ERA_MAP or
            current_era == "Home" or
            current_era == "Mega"
        )

        if needs_fix:
            wizard_entry = find_wizard_entry(set_name, wizard_index)
            if wizard_entry:
                _, raw_era = fetch_wizard_era(wizard_entry["url"])
                if raw_era:
                    fixed = normalise_era(raw_era)
                    updates.append(gspread.Cell(i, COL["era"], fixed))
                    print(f"    Era fix: '{set_name}' -> '{fixed}' (was '{current_era}')")
            elif current_era:
                fixed = normalise_era(current_era)
                if fixed != current_era:
                    updates.append(gspread.Cell(i, COL["era"], fixed))
                    print(f"    Era normalised: '{set_name}' -> '{fixed}'")

    if updates:
        try:
            ws.update_cells(updates, value_input_option='USER_ENTERED')
            print(f"  Era backfill: fixed {len(updates)} rows")
        except Exception as e:
            print(f"  [WARN] Era backfill failed: {e}")
    else:
        print("  Era backfill: all rows correct")

def fetch_wizard_era(set_url):
    try:
        r = requests.get(set_url, timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        return None, None

    era = None
    date_str = None

    h1 = soup.find("h1")
    if h1:
        prev = h1.find_previous_sibling("h3")
        if prev:
            era = prev.get_text(strip=True)

    if not era:
        for p in soup.find_all("p"):
            m = re.search(r'part of the ([^,]+) series', p.get_text(strip=True))
            if m:
                era = m.group(1).strip()
                break

    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        m = re.search(r'Released on (\w+ \d+, \d{4})', text)
        if m:
            try:
                dt = datetime.datetime.strptime(m.group(1), "%B %d, %Y")
                date_str = dt.strftime("%b-%y")
            except ValueError:
                pass
            break

    return date_str, era

# ── Exchange rate ─────────────────────────────────────────────────────────────
def get_usd_to_gbp():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        return r.json()["rates"]["GBP"]
    except Exception as e:
        print(f"  [WARN] Exchange rate fetch failed: {e} - using 0.79")
        return 0.79

# ── Dawnglare scraper ─────────────────────────────────────────────────────────
def fetch_dawnglare_prices():
    print("  Fetching dawnglare.com ...")
    try:
        resp = cffi_requests.get("https://pokemon.dawnglare.com/?p=boxprice", impersonate="chrome110", timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] dawnglare fetch failed: {e}")
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    prices = {}
    for a_tag in soup.find_all("a", href=True):
        name = a_tag.get_text(strip=True)
        td = a_tag.find_parent("td")
        if not td:
            continue
        next_td = td.find_next_sibling("td")
        if not next_td:
            continue
        span = next_td.find("span", class_=re.compile(r'^pi\d+$'))
        if not span:
            continue
        price_text = span.get_text(strip=True).replace("$", "").replace(",", "")
        try:
            prices[name.lower()] = float(price_text)
        except ValueError:
            continue

    print(f"  dawnglare: found {len(prices)} entries")
    return prices

def find_booster_box_price(set_name, dawnglare_prices):
    key = set_name.strip().lower()
    mapped = DAWNGLARE_MAP.get(key, key)

    if mapped + " booster box" in dawnglare_prices:
        return dawnglare_prices[mapped + " booster box"], "BB"
    if mapped + " enhanced booster box" in dawnglare_prices:
        return dawnglare_prices[mapped + " enhanced booster box"], "Enhanced BB"

    key_words = set(mapped.split()) - {"the", "and", "&", "of", "a"}
    bb_candidates = {n: p for n, p in dawnglare_prices.items() if "booster box" in n}
    best_score, best_name, best_price = 0, None, None
    for dg_name, price in bb_candidates.items():
        score = len(key_words & set(dg_name.split()))
        if score > best_score:
            best_score, best_name, best_price = score, dg_name, price
    if best_score >= 2:
        return best_price, f"BB~{best_name}"

    if key in ETB_ONLY_SETS:
        etb_fragment = ETB_ONLY_SETS[key]
        for dg_name, price in dawnglare_prices.items():
            if etb_fragment in dg_name and "exclusive" not in dg_name and "set of" not in dg_name:
                return price * 4, "ETBx4"

    return None, "NOT FOUND"


# ── TCGCSV fallback price lookup ──────────────────────────────────────────────
def fetch_tcgcsv_bb_price(set_name, rate, pg_conn):
    """
    Fallback: look up booster box price from tcgcsv_prices via tcgcsv_bb_product_id.
    Used when Dawnglare returns None for a set. Returns (gbp_price, source_label) or (None, None).
    Cron safety: read-only query — does not affect score_sets.py or generate_blog_posts.py.
    """
    if not pg_conn or not DATABASE_URL:
        return None, None
    try:
        import psycopg2.extras as _pge
        cur = pg_conn.cursor(cursor_factory=_pge.RealDictCursor)
        # Look up the tcgcsv_bb_product_id for this set
        cur.execute(
            "SELECT tcgcsv_bb_product_id FROM sets WHERE name = %s",
            (set_name,)
        )
        row = cur.fetchone()
        if not row or not row["tcgcsv_bb_product_id"]:
            return None, None
        pid = row["tcgcsv_bb_product_id"]
        # Get latest price from tcgcsv_prices
        cur.execute("""
            SELECT market_price_usd
            FROM tcgcsv_prices
            WHERE product_id = %s AND sub_type_name = 'Normal' AND market_price_usd IS NOT NULL
            ORDER BY snapshot_date DESC
            LIMIT 1
        """, (pid,))
        price_row = cur.fetchone()
        if not price_row:
            return None, None
        usd = float(price_row["market_price_usd"])
        gbp = round(usd * rate, 2)
        return gbp, "tcgcsv"
    except Exception as e:
        print(f"    [WARN] TCGCSV fallback failed for {set_name}: {e}")
        return None, None

# ── PokemonWizard ─────────────────────────────────────────────────────────────
def fetch_wizard_index():
    print("  Fetching PokemonWizard set index ...")
    try:
        r = requests.get(f"{WIZARD_BASE}/sets", timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [ERROR] Wizard index fetch failed: {e}")
        return {}

    index = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.match(r'^/sets/\d+/', href):
            continue
        name = a.get_text(strip=True)
        if name and name != "Buy":
            index[name.lower()] = {"url": WIZARD_BASE + href, "name": name}

    print(f"  Wizard index: {len(index)} sets")
    return index

def find_wizard_entry(set_name, wizard_index):
    key = set_name.strip().lower()
    mapped = WIZARD_NAME_MAP.get(key, set_name).lower()

    if mapped in wizard_index:
        return wizard_index[mapped]
    if key in wizard_index:
        return wizard_index[key]

    key_words = set(mapped.split()) - {"the", "and", "&", "of", "a"}
    best_score, best_entry = 0, None
    for wname, entry in wizard_index.items():
        score = len(key_words & set(wname.split()))
        if score > best_score:
            best_score, best_entry = score, entry
    if best_score >= 2:
        return best_entry
    return None

def fetch_wizard_set_data(set_url, rate):
    try:
        r = requests.get(set_url, timeout=20, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"    [WARN] Wizard page fetch failed: {e}")
        return None, []

    total_usd = None
    for strong in soup.find_all("strong"):
        if strong.get_text(strip=True) == "Total Value":
            row = strong.find_parent("tr")
            if row:
                span = row.find("span", class_=re.compile(r"text-(danger|success)"))
                if span:
                    val_text = span.get_text(strip=True).replace("$", "").replace(",", "").split()[0]
                    try:
                        total_usd = float(val_text)
                    except ValueError:
                        pass
            break

    cards = []
    for row in soup.select("tr"):
        tds = row.find_all("td")
        if len(tds) < 5:
            continue
        price_text = tds[4].get_text(strip=True).replace("$", "").replace(",", "")
        try:
            price = float(price_text)
        except ValueError:
            continue
        raw_name = tds[1].get_text(strip=True)
        name = re.sub(r'\s+\d+\s+\d+\s*$', '', raw_name).strip()
        if name:
            cards.append((name, price))

    return total_usd, cards

def fetch_wizard_combined(set_name, wizard_entry, wizard_index, rate):
    key = set_name.strip().lower()

    base_total_usd, base_cards = fetch_wizard_set_data(wizard_entry["url"], rate)
    all_cards = list(base_cards)
    combined_total_usd = base_total_usd or 0

    sub_set_fragments = SUBSET_MAP.get(key, [])
    seen_sub_urls = set()
    for fragment in sub_set_fragments:
        sub_entry = wizard_index.get(fragment)
        if not sub_entry:
            for wname, entry in wizard_index.items():
                if wname == fragment:
                    sub_entry = entry
                    break
        if sub_entry and sub_entry["url"] not in seen_sub_urls:
            seen_sub_urls.add(sub_entry["url"])
            sub_total_usd, sub_cards = fetch_wizard_set_data(sub_entry["url"], rate)
            if sub_total_usd:
                combined_total_usd += sub_total_usd
                existing_names = {n for n, _ in all_cards}
                for name, price in sub_cards:
                    if name not in existing_names:
                        all_cards.append((name, price))
                        existing_names.add(name)
                print(f"      + Sub-set: {sub_entry['name']} (${sub_total_usd:.2f})")

    if combined_total_usd == 0:
        return None, None, None

    seen_names = {}
    for name, price in all_cards:
        clean_name = re.sub(r'\s+\d+\s+\d+\s*$', '', name).strip()
        if clean_name and (clean_name not in seen_names or price > seen_names[clean_name]):
            seen_names[clean_name] = price
    deduped = sorted(seen_names.items(), key=lambda x: x[1], reverse=True)
    top3 = deduped[:3]
    top3_str = ", ".join(n for n, _ in top3) if top3 else None
    top3_usd_sum = sum(p for _, p in top3) if top3 else None
    total_gbp = round(combined_total_usd * rate, 2)

    return total_gbp, top3_str, top3_usd_sum

# ── New set detection ─────────────────────────────────────────────────────────
def detect_new_sets(ws, wizard_index):
    all_rows = ws.get_all_values()
    existing_names = set()
    for row in all_rows[1:]:
        if len(row) >= 3 and row[2].strip():
            name = row[2].strip().lower()
            existing_names.add(name)
            mapped = WIZARD_NAME_MAP.get(name, "").lower()
            if mapped:
                existing_names.add(mapped)

    cutoff = datetime.datetime.now() - datetime.timedelta(days=NEW_SET_DAYS)
    new_sets = []

    for wname, entry in wizard_index.items():
        if wname in existing_names:
            continue
        date_str, _ = fetch_wizard_era(entry["url"])
        if not date_str:
            continue
        try:
            dt = datetime.datetime.strptime(date_str, "%b-%y")
            if dt >= cutoff:
                entry["date_str"] = date_str
                new_sets.append(entry)
        except ValueError:
            continue

    return new_sets

# ── Groq scoring ──────────────────────────────────────────────────────────────
def call_groq(set_data):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("    [WARN] No GROQ_API_KEY found, skipping scoring")
        return None

    prompt = f"""You are a Pokemon TCG investment analyst. Score this set and provide a recommendation.

Set: {set_data.get('name', '')}
Release Date: {set_data.get('date', 'Unknown')}
Era: {set_data.get('era', 'Unknown')}
BB Price (GBP): {set_data.get('bb_price', 'Unknown')}
Set Value (GBP): {set_data.get('set_value', 'Unknown')}
Top 3 Chase Cards: {set_data.get('chase', 'Unknown')}
Box %: {set_data.get('box_pct', 'Unknown')}
Chase Card %: {set_data.get('chase_pct', 'Unknown')}
Print Status: {set_data.get('print_status', 'Unknown')}

Score each category as an integer 1-5:

L Scarcity (investment timing focus - NOT just out of print status):
5 = Recently went OOP within 2 years - price still adjusting upward, buy window open
4 = OOP 2-4 years - established premium but still some upside
3 = OOP 4+ years - fully priced in by market, limited upside, opportunity has passed
2 = Still in print, approaching OOP within 12 months
1 = Heavily restocked, reprinted, or widely available

M Liquidity:
5 = Booster Box, fast sell, high demand
3 = Mixed products, moderate demand
1 = Collection box only, slow sell, niche demand

N Mascot Power:
5 = Charizard/Eevee/Umbreon as PRIMARY chase card
4 = One of those as secondary chase, other strong pulls
3 = Popular Pokemon but not top tier mascots
2 = Niche Pokemon with small fanbase
1 = No recognisable chase cards, weak pull rates

O Set Depth:
5 = Many Illustration Rares spread across set, multiple chase tiers
3 = Several good cards, some depth
1 = Only 1-2 good cards, rest worthless

IMPORTANT SCORING RULES:
- Sets still IN PRINT must score L=1 or L=2 maximum.
- Sets out of print for 4+ years score L=3 maximum.
- Only sets that went OOP within the last 2 years should score L=4 or L=5.
- High Scarcity does NOT automatically mean a good investment.
- Current in-print sets (2024-2026 releases still printing): Perfect Order, Ascended Heroes,
  Phantasmal Flames, Black Bolt, White Flare, Destined Rivals, Journey Together,
  Prismatic Evolutions, Surging Sparks, Stellar Crown, Twilight Masquerade,
  Temporal Forces, Paradox Rift, Obsidian Flames, Paldea Evolved, S&V Base Set
  - these must ALL score L=1 or L=2.

H recommendation must be exactly one of: Strong Buy, Buy, Accumulate, Hold, Overvalued

RECOMMENDATION RULES (follow exactly):
- Box % > 100%: always Overvalued, no exceptions
- In print sets: maximum Accumulate, never Buy or Strong Buy
- Strong Buy: box % under 50%, OOP under 2 years, strong mascot, deep set
- Buy: box % 50-75%, OOP within 2 years, decent mascot
- Accumulate: approaching OOP, or box % 60-75% OOP 2-4 years
- Hold: box % 75-100%, OOP or aging

Respond in JSON only, no other text:
{{"L": int, "M": int, "N": int, "O": int, "H": "recommendation"}}"""

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,
        "temperature": 0.1
    }

    try:
        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        text = re.sub(r'```json|```', '', text).strip()
        result = json.loads(text)
        for k in ["L", "M", "N", "O"]:
            result[k] = max(1, min(5, int(result[k])))
        if result.get("H") not in VALID_RECOMMENDATIONS:
            result["H"] = "Hold"
        return result
    except Exception as e:
        print(f"    [WARN] Groq call failed: {e}")
        return None

# ── Conditional formatting ────────────────────────────────────────────────────
def hex_to_rgb(hex_color):
    h = hex_color.lstrip('#')
    return {
        "red":   int(h[0:2], 16) / 255,
        "green": int(h[2:4], 16) / 255,
        "blue":  int(h[4:6], 16) / 255
    }

def _cell_format(sheet_id, row_idx, col_idx, bg_hex, text_hex):
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row_idx,
                "endRowIndex": row_idx + 1,
                "startColumnIndex": col_idx,
                "endColumnIndex": col_idx + 1
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb(bg_hex),
                    "textFormat": {
                        "foregroundColor": hex_to_rgb(text_hex),
                        "bold": False
                    }
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat.foregroundColor"
        }
    }

def apply_number_formats(ws, sh, num_rows):
    try:
        sh.batch_update({"requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": 1,
                        "endRowIndex": num_rows + 1,
                        "startColumnIndex": COL["box_pct"] - 1,
                        "endColumnIndex": COL["box_pct"]
                    },
                    "cell": {"userEnteredFormat": {
                        "numberFormat": {"type": "PERCENT", "pattern": "0.0%"}
                    }},
                    "fields": "userEnteredFormat.numberFormat"
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": 1,
                        "endRowIndex": num_rows + 1,
                        "startColumnIndex": COL["chase_pct"] - 1,
                        "endColumnIndex": COL["chase_pct"]
                    },
                    "cell": {"userEnteredFormat": {
                        "numberFormat": {"type": "NUMBER", "pattern": "0.00"}
                    }},
                    "fields": "userEnteredFormat.numberFormat"
                }
            }
        ]})
        print("  Number formats applied (G=%, I=0.00)")
    except Exception as e:
        print(f"  [WARN] Number format failed: {e}")

def apply_conditional_formatting(ws, sh, all_rows):
    sheet_id = ws.id
    requests_batch = []

    for i, row in enumerate(all_rows[1:], start=2):
        def col_val(col_key):
            idx = COL[col_key] - 1
            return str(row[idx]).strip() if idx < len(row) else ""

        try:
            g_val = float(col_val("box_pct").replace("%", ""))
            if g_val > 1.0:
                g_val = g_val / 100
            if g_val > 1.0:
                bg, fg = "#FFCCCC", "#CC0000"
            elif g_val >= 0.75:
                bg, fg = "#FFE5CC", "#CC6600"
            elif g_val >= 0.5:
                bg, fg = "#FFFACC", "#806600"
            else:
                bg, fg = "#CCFFCC", "#006600"
            requests_batch.append(_cell_format(sheet_id, i-1, COL["box_pct"]-1, bg, fg))
        except (ValueError, TypeError):
            pass

        try:
            i_val = float(col_val("chase_pct").replace("%", ""))
            if i_val > 1.0:
                i_val = i_val / 100
            if i_val > 0.5:
                bg, fg = "#FFCCCC", "#CC0000"
            else:
                bg, fg = "#CCFFCC", "#006600"
            requests_batch.append(_cell_format(sheet_id, i-1, COL["chase_pct"]-1, bg, fg))
        except (ValueError, TypeError):
            pass

        try:
            k_val = int(float(col_val("decision")))
            if k_val >= 16:
                bg, fg = "#CCFFCC", "#006600"
            elif k_val >= 12:
                bg, fg = "#CCE5FF", "#003399"
            elif k_val >= 8:
                bg, fg = "#FFFACC", "#806600"
            elif k_val >= 4:
                bg, fg = "#FFE5CC", "#CC6600"
            else:
                bg, fg = "#FFCCCC", "#CC0000"
            requests_batch.append(_cell_format(sheet_id, i-1, COL["decision"]-1, bg, fg))
        except (ValueError, TypeError):
            pass

        try:
            date_str = col_val("date")
            print_status = col_val("print_status").lower()
            if date_str and "in print" not in print_status:
                dt = datetime.datetime.strptime(date_str, "%b-%y")
                today = date.today()
                months_ago = (today.year - dt.year) * 12 + (today.month - dt.month)
                if months_ago > 24:
                    requests_batch.append(_cell_format(sheet_id, i-1, COL["date"]-1, "#FFCCCC", "#CC0000"))
                elif months_ago >= 18:
                    requests_batch.append(_cell_format(sheet_id, i-1, COL["date"]-1, "#FFFACC", "#806600"))
        except (ValueError, TypeError):
            pass

    for batch_start in range(0, len(requests_batch), 50):
        try:
            sh.batch_update({"requests": requests_batch[batch_start:batch_start+50]})
            time.sleep(2)
        except Exception as e:
            print(f"  [WARN] Formatting batch failed: {e}")

# ── SQLite writer ─────────────────────────────────────────────────────────────
def write_to_sqlite(run_date, rate, sqlite_rows, sqlite_score_results, new_sets_count):
    """
    Write monthly run results to Postgres (and SQLite as fallback).
    Upserts sets, inserts/updates monthly_snapshots and scores, logs the run.
    Google Sheets is unaffected - this is an additional write target only.
    """
    # ── Postgres write ────────────────────────────────────────────────────────
    if DATABASE_URL:
        try:
            pg  = psycopg2.connect(DATABASE_URL)
            pg.cursor_factory = psycopg2.extras.RealDictCursor
            cur = pg.cursor()

            sets_written = 0
            sets_scored  = 0

            for row in sqlite_rows:
                set_name = row.get("name", "").strip()
                if not set_name:
                    continue

                cur.execute("""
                    INSERT INTO sets (name, era, date_released, print_status, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT(name) DO UPDATE SET
                        era           = EXCLUDED.era,
                        date_released = EXCLUDED.date_released,
                        print_status  = EXCLUDED.print_status,
                        updated_at    = NOW()
                """, (
                    set_name,
                    row.get("era", ""),
                    row.get("date", ""),
                    row.get("print_status", ""),
                ))

                cur.execute("SELECT id FROM sets WHERE name = %s", (set_name,))
                set_id = cur.fetchone()["id"]

                cur.execute("""
                    INSERT INTO monthly_snapshots
                        (set_id, run_date, bb_price_gbp, set_value_gbp,
                         top3_chase, box_pct, chase_pct, price_source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(set_id, run_date) DO UPDATE SET
                        bb_price_gbp  = EXCLUDED.bb_price_gbp,
                        set_value_gbp = EXCLUDED.set_value_gbp,
                        top3_chase    = EXCLUDED.top3_chase,
                        box_pct       = EXCLUDED.box_pct,
                        chase_pct     = EXCLUDED.chase_pct,
                        price_source  = EXCLUDED.price_source
                """, (
                    set_id,
                    run_date,
                    row.get("bb_price_gbp"),
                    row.get("set_value_gbp"),
                    row.get("top3_chase"),
                    row.get("box_pct"),
                    row.get("chase_pct"),
                    row.get("price_source", "dawnglare+wizard"),
                ))
                sets_written += 1

                groq = sqlite_score_results.get(set_name)
                if groq:
                    k = groq["L"] + groq["M"] + groq["N"] + groq["O"]
                    cur.execute("""
                        INSERT INTO scores
                            (set_id, run_date, recommendation, scarcity,
                             liquidity, mascot_power, set_depth, decision_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(set_id, run_date) DO UPDATE SET
                            recommendation = EXCLUDED.recommendation,
                            scarcity       = EXCLUDED.scarcity,
                            liquidity      = EXCLUDED.liquidity,
                            mascot_power   = EXCLUDED.mascot_power,
                            set_depth      = EXCLUDED.set_depth,
                            decision_score = EXCLUDED.decision_score
                    """, (
                        set_id, run_date,
                        groq["H"], groq["L"], groq["M"], groq["N"], groq["O"], k
                    ))
                    sets_scored += 1

            cur.execute("""
                INSERT INTO run_log
                    (run_date, sets_updated, sets_added, sets_scored, usd_gbp_rate, status)
                VALUES (%s, %s, %s, %s, %s, 'success')
            """, (run_date, sets_written, new_sets_count, sets_scored, rate))

            cur.execute("""
                UPDATE scores SET recommendation = 'Overvalued'
                WHERE run_date = %s
                AND (SELECT box_pct FROM monthly_snapshots m
                     WHERE m.set_id = scores.set_id
                     AND m.run_date = scores.run_date) > 1.0
            """, (run_date,))

            pg.commit()
            cur.close()
            pg.close()
            print(f"  Postgres: {sets_written} snapshots written, {sets_scored} scores written")
        except Exception as e:
            print(f"  Postgres write FAILED: {e}")
            print(f"  Falling back to SQLite...")

    # ── SQLite fallback ───────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    sets_written = 0
    sets_scored  = 0

    for row in sqlite_rows:
        set_name = row.get("name", "").strip()
        if not set_name:
            continue

        cur.execute("""
            INSERT INTO sets (name, era, date_released, print_status, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(name) DO UPDATE SET
                era           = excluded.era,
                date_released = excluded.date_released,
                print_status  = excluded.print_status,
                updated_at    = datetime('now')
        """, (
            set_name,
            row.get("era", ""),
            row.get("date", ""),
            row.get("print_status", ""),
        ))

        cur.execute("SELECT id FROM sets WHERE name = ?", (set_name,))
        set_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO monthly_snapshots
                (set_id, run_date, bb_price_gbp, set_value_gbp,
                 top3_chase, box_pct, chase_pct, price_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(set_id, run_date) DO UPDATE SET
                bb_price_gbp  = excluded.bb_price_gbp,
                set_value_gbp = excluded.set_value_gbp,
                top3_chase    = excluded.top3_chase,
                box_pct       = excluded.box_pct,
                chase_pct     = excluded.chase_pct,
                price_source  = excluded.price_source
        """, (
            set_id,
            run_date,
            row.get("bb_price_gbp"),
            row.get("set_value_gbp"),
            row.get("top3_chase"),
            row.get("box_pct"),
            row.get("chase_pct"),
            row.get("price_source", "dawnglare+wizard"),
        ))
        sets_written += 1

        groq = sqlite_score_results.get(set_name)
        if groq:
            k = groq["L"] + groq["M"] + groq["N"] + groq["O"]
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
            """, (
                set_id, run_date,
                groq["H"], groq["L"], groq["M"], groq["N"], groq["O"], k
            ))
            sets_scored += 1

    cur.execute("""
        INSERT INTO run_log
            (run_date, sets_updated, sets_added, sets_scored, usd_gbp_rate, status)
        VALUES (?, ?, ?, ?, ?, 'success')
    """, (run_date, sets_written, new_sets_count, sets_scored, rate))

    cur.execute("""
        UPDATE scores SET recommendation = 'Overvalued'
        WHERE run_date = ?
        AND (SELECT box_pct FROM monthly_snapshots m
             WHERE m.set_id = scores.set_id
             AND m.run_date = scores.run_date) > 1.0
    """, (run_date,))

    conn.commit()
    conn.close()
    print(f"  SQLite fallback: {sets_written} snapshots written, {sets_scored} scores written")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    today = date.today()
    print(f"=== Pokemon Tracker v3 === {today} ===")

    print("\n[1/9] Connecting to Google Sheets ...")
    sh, config = connect_sheets()
    print(f"  Connected: {sh.title}")

    print("\n[2/9] Backing up ...")
    backup_sheet(sh)

    print("\n[3/9] Setting up monthly sheet ...")
    ws = get_or_create_monthly_sheet(sh)

    rate = get_usd_to_gbp()
    print(f"\n  USD->GBP rate: {rate:.4f}")

    print("\n[4/9] Fetching price data sources ...")
    dawnglare    = fetch_dawnglare_prices()
    wizard_index = fetch_wizard_index()

    # Open Postgres connection for TCGCSV fallback (read-only)
    _pg_fallback = None
    if DATABASE_URL:
        try:
            _pg_fallback = psycopg2.connect(DATABASE_URL)
            print("  Postgres fallback connection: OK")
        except Exception as _e:
            print(f"  [WARN] Postgres fallback connection failed: {_e}")

    print("\n[5/9] Era backfill ...")
    backfill_era(ws, sh, wizard_index)

    print(f"\n[6/9] Checking for new sets (last {NEW_SET_DAYS} days) ...")
    new_sets = detect_new_sets(ws, wizard_index)
    if new_sets:
        print(f"  Found {len(new_sets)} new sets: {[s['name'] for s in new_sets]}")
        for entry in new_sets:
            date_str, raw_era = fetch_wizard_era(entry["url"])
            era_code = normalise_era(raw_era) if raw_era else ""
            new_row = [""] * 15
            new_row[COL["era"]-1]  = era_code
            new_row[COL["date"]-1] = entry.get("date_str", date_str or "")
            new_row[COL["name"]-1] = entry["name"]
            ws.append_row(new_row, value_input_option='USER_ENTERED')
            print(f"    Added: {entry['name']} | Era: {era_code} | Date: {new_row[COL['date']-1]}")
    else:
        print("  No new sets found")

    print("\n[7/9] Updating prices ...")
    all_rows    = ws.get_all_values()
    updates     = []
    score_queue = []

    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) < 3 or not row[2].strip():
            continue

        set_name = row[2].strip()
        print(f"\n  Row {i}: {set_name}")

        usd_price, note = find_booster_box_price(set_name, dawnglare)
        gbp = None
        price_source_override = None
        if usd_price is not None:
            gbp = round(usd_price * rate, 2)
            updates.append((i, COL["bb_price"], gbp))
            print(f"    D: {gbp:.2f} [{note}]")
        else:
            print(f"    D: NOT FOUND — trying TCGCSV fallback ...")
            gbp_fallback, fallback_src = fetch_tcgcsv_bb_price(set_name, rate, _pg_fallback)
            if gbp_fallback is not None:
                gbp = gbp_fallback
                price_source_override = "tcgcsv"
                updates.append((i, COL["bb_price"], gbp))
                print(f"    D: {gbp:.2f} [tcgcsv fallback]")
            else:
                print(f"    D: NOT FOUND (no fallback available)")

        wizard_entry  = find_wizard_entry(set_name, wizard_index)
        set_value_gbp = None
        top3_usd_sum  = None
        chase_str     = None
        if wizard_entry:
            set_value_gbp, chase_str, top3_usd_sum = fetch_wizard_combined(
                set_name, wizard_entry, wizard_index, rate
            )
            if set_value_gbp is not None:
                updates.append((i, COL["set_value"], set_value_gbp))
                print(f"    E: {set_value_gbp:.2f}")
            if chase_str:
                updates.append((i, COL["chase"], chase_str))
                print(f"    F: {chase_str}")
        else:
            print(f"    E/F: no Wizard match")

        box_pct = None
        if gbp and set_value_gbp and set_value_gbp > 0:
            box_pct = round(gbp / set_value_gbp, 4)
            updates.append((i, COL["box_pct"], box_pct))
            print(f"    G: {box_pct:.1%}")

        chase_pct = None
        if top3_usd_sum and set_value_gbp and set_value_gbp > 0:
            top3_gbp  = round(top3_usd_sum * rate, 2)
            chase_pct = round(top3_gbp / set_value_gbp, 4)
            updates.append((i, COL["chase_pct"], chase_pct))
            print(f"    I: {chase_pct:.2f}")

        score_queue.append({
            "row_idx":      i,
            "name":         set_name,
            "era":          row[COL["era"]-1]          if len(row) > COL["era"]-1          else "",
            "date":         row[COL["date"]-1]         if len(row) > COL["date"]-1         else "",
            "bb_price":     gbp,
            "set_value":    set_value_gbp,
            "chase":        chase_str or (row[COL["chase"]-1] if len(row) > COL["chase"]-1 else ""),
            "box_pct":      f"{box_pct:.1%}"   if box_pct   else "",
            "chase_pct":    f"{chase_pct:.2f}" if chase_pct else "",
            "print_status": row[COL["print_status"]-1] if len(row) > COL["print_status"]-1 else "",
            "price_source_override": price_source_override,
        })

    print(f"\n  Writing {len(updates)} cell updates ...")
    try:
        for batch_start in range(0, len(updates), 200):
            batch     = updates[batch_start:batch_start+200]
            cell_list = [gspread.Cell(r, c, v) for r, c, v in batch]
            ws.update_cells(cell_list, value_input_option='USER_ENTERED')
            time.sleep(2)
        print("  Price updates written")
    except Exception as e:
        print(f"  [ERROR] Failed to write updates: {e}")

    apply_number_formats(ws, sh, len(all_rows) - 1)

    print(f"\n[8/9] Groq scoring ({len(score_queue)} sets) ...")
    score_updates        = []
    sqlite_score_results = {}

    for idx, item in enumerate(score_queue):
        print(f"  [{idx+1}/{len(score_queue)}] {item['name']} ...")
        result = call_groq(item)
        if result:
            sqlite_score_results[item["name"]] = result
            row_idx = item["row_idx"]
            k = result["L"] + result["M"] + result["N"] + result["O"]
            score_updates.extend([
                gspread.Cell(row_idx, COL["recommendation"], result["H"]),
                gspread.Cell(row_idx, COL["scarcity"],       result["L"]),
                gspread.Cell(row_idx, COL["liquidity"],      result["M"]),
                gspread.Cell(row_idx, COL["mascot"],         result["N"]),
                gspread.Cell(row_idx, COL["depth"],          result["O"]),
                gspread.Cell(row_idx, COL["decision"],       k),
            ])
            print(f"    H={result['H']} L={result['L']} M={result['M']} N={result['N']} O={result['O']} K={k}")
        time.sleep(2)

        if len(score_updates) >= 60:
            try:
                ws.update_cells(score_updates, value_input_option='USER_ENTERED')
                score_updates = []
                time.sleep(2)
            except Exception as e:
                print(f"  [WARN] Score batch write failed: {e}")

    if score_updates:
        try:
            ws.update_cells(score_updates, value_input_option='USER_ENTERED')
        except Exception as e:
            print(f"  [WARN] Final score write failed: {e}")

    print("  Scoring complete")

    print("\n  Applying conditional formatting ...")
    all_rows = ws.get_all_values()
    apply_conditional_formatting(ws, sh, all_rows)

    # ── Write to SQLite ───────────────────────────────────────────────────────
    print(f"\n[9/9] Writing to SQLite ...")
    run_date    = today.strftime("%Y-%m-%d")
    if _pg_fallback:
        try:
            _pg_fallback.close()
        except Exception:
            pass

    sqlite_rows = []
    for item in score_queue:
        src = item.get("price_source_override") or "dawnglare+wizard"
        sqlite_rows.append({
            "name":          item["name"],
            "era":           item["era"],
            "date":          item["date"],
            "print_status":  item["print_status"],
            "bb_price_gbp":  item["bb_price"],
            "set_value_gbp": item["set_value"],
            "top3_chase":    item["chase"],
            "box_pct":       item["box_pct"],
            "chase_pct":     item["chase_pct"],
            "price_source":  src,
        })

    write_to_sqlite(run_date, rate, sqlite_rows, sqlite_score_results, len(new_sets))

    print(f"\n{'='*50}")
    print(f"  New sets added : {len(new_sets)}")
    print(f"  Price updates  : {len(updates)} cells")
    print(f"  Sets scored    : {len(score_queue)}")

if __name__ == "__main__":
    main()
