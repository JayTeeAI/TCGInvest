#!/usr/bin/env python3
"""
Pokemon Booster Box Tracker — v2 Monthly Updater
- Reads/writes Google Sheets
- Detects new sets from PokemonWizard (last 60 days only)
- Scores sets via Gemini 2.5 Flash
- Backs up before each run
"""

import re
import os
import json
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
LOCAL_EXCEL      = "/root/.openclaw/workspace/pokemon-tracker.xlsx"
BACKUP_DIR       = "/root/.openclaw/workspace/backups"
JAYTEE_COPY      = "/home/jaytee/pokemon-tracker.xlsx"
WIZARD_BASE      = "https://www.pokemonwizard.com"
HEADERS          = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
PROTECTED_SHEETS = {"Selling Individual Cards"}
NEW_SET_DAYS     = 60  # only add sets released within this many days

# Column indices (1-based for gspread)
COL = {
    "era": 1, "date": 2, "name": 3, "bb_price": 4, "set_value": 5,
    "chase": 6, "box_pct": 7, "recommendation": 8, "chase_pct": 9,
    "print_status": 10, "decision": 11, "scarcity": 12,
    "liquidity": 13, "mascot": 14, "depth": 15
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

VALID_RECOMMENDATIONS = {"Strong Buy", "Buy", "Accumulate", "Hold", "Reduce", "Sell", "Overvalued"}

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
    return sh, config, gc

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# ── Backup ────────────────────────────────────────────────────────────────────
def backup_sheet(sh, gc):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    today_str = date.today().strftime("%Y-%m-%d")
    backup_path = os.path.join(BACKUP_DIR, f"pokemon-tracker-backup-{today_str}.xlsx")
    try:
        import google.auth.transport.requests
        req = google.auth.transport.requests.Request()
        creds_obj = Credentials.from_service_account_file(CREDENTIALS_FILE, 
            scopes=["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"])
        creds_obj.refresh(req)
        token = creds_obj.token
        url = f"https://docs.google.com/spreadsheets/d/{sh.id}/export?format=xlsx"
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        with open(backup_path, "wb") as f:
            f.write(r.content)
        print(f"  Backup saved: {backup_path}")
    except Exception as e:
        print(f"  [WARN] Backup failed: {e}")
        return

    # Keep only 3 most recent
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

    # Move to position 0
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

# ── Exchange rate ─────────────────────────────────────────────────────────────
def get_usd_to_gbp():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        return r.json()["rates"]["GBP"]
    except Exception as e:
        print(f"  [WARN] Exchange rate fetch failed: {e} — using 0.79")
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

def fetch_wizard_set_page(set_url, rate):
    """Returns (total_value_gbp, top3_str, top3_usd_sum)"""
    try:
        r = requests.get(set_url, timeout=20, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"    [WARN] Wizard page fetch failed: {e}")
        return None, None, None

    # Total value
    total_val_usd = None
    for strong in soup.find_all("strong"):
        if strong.get_text(strip=True) == "Total Value":
            row = strong.find_parent("tr")
            if row:
                span = row.find("span", class_=re.compile(r"text-(danger|success)"))
                if span:
                    val_text = span.get_text(strip=True).replace("$", "").replace(",", "").split()[0]
                    try:
                        total_val_usd = float(val_text)
                    except ValueError:
                        pass
            break

    # Top 3 cards by price
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

    cards.sort(key=lambda x: x[1], reverse=True)
    top3 = cards[:3]
    top3_str = ", ".join(n for n, _ in top3) if top3 else None
    top3_usd_sum = sum(p for _, p in top3) if top3 else None
    total_gbp = round(total_val_usd * rate, 2) if total_val_usd else None
    return total_gbp, top3_str, top3_usd_sum

def fetch_wizard_set_details(set_url):
    """Scrape Era and Date Released. Returns (era_str, date_str)"""
    try:
        r = requests.get(set_url, timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"    [WARN] Set detail fetch failed: {e}")
        return None, None

    era = None
    date_str = None

    # Era — it's the <h3> tag immediately before the <h1> set name
    h1 = soup.find("h1")
    if h1:
        prev = h1.find_previous_sibling("h3")
        if prev:
            era = prev.get_text(strip=True)
    # Fallback: check the About paragraph "part of the X series"
    if not era:
        for p in soup.find_all("p"):
            m = re.search(r'part of the ([^,]+) series', p.get_text(strip=True))
            if m:
                era = m.group(1).strip()
                break

    # Date — "Released on Month DD, YYYY"
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

    return era, date_str

# ── New set detection ─────────────────────────────────────────────────────────
def detect_new_sets(ws, wizard_index):
    """
    Compare PokemonWizard index against sheet Column C.
    Only return sets released within NEW_SET_DAYS days.
    """
    all_rows = ws.get_all_values()

    # Build normalised set of existing names — handle name map variants
    existing_names = set()
    for row in all_rows[1:]:
        if len(row) >= 3 and row[2].strip():
            name = row[2].strip().lower()
            existing_names.add(name)
            # Also add the wizard-mapped version
            mapped = WIZARD_NAME_MAP.get(name, "").lower()
            if mapped:
                existing_names.add(mapped)

    cutoff = datetime.datetime.now() - datetime.timedelta(days=NEW_SET_DAYS)
    new_sets = []

    for wname, entry in wizard_index.items():
        # Skip if already in sheet
        if wname in existing_names:
            continue

        # Fetch set page to get release date before deciding to add
        _, date_str = fetch_wizard_set_details(entry["url"])
        if not date_str:
            continue  # can't determine date, skip

        try:
            dt = datetime.datetime.strptime(date_str, "%b-%y")
            if dt >= cutoff:
                entry["date_str"] = date_str
                new_sets.append(entry)
        except ValueError:
            continue

    return new_sets

# ── Gemini scoring ────────────────────────────────────────────────────────────
def call_gemini(set_data):
    """Scoring via Groq (Llama 3.3 70b) — no rate limit issues on free tier."""
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
- L Scarcity: 5=Out of Print, 4=Going OOP soon (18-24mo), 3=18mo old still printing, 2=In print under 18mo, 1=Heavily restocked
- M Format Liquidity: 5=Booster Box easy sell, 3=Mixed products, 1=Collection box only slow sell
- N Mascot Power: 5=Charizard/Eevee/Umbreon top chase, 3=Popular but not top tier, 1=No big chase cards
- O Set Depth: 5=Many Illustration Rares spread across set, 3=Several good cards, 1=Only 1-2 good cards

Column H recommendation must be exactly one of: Strong Buy, Buy, Accumulate, Hold, Reduce, Sell, Overvalued

Respond in JSON only, no other text:
{{"L": int, "M": int, "N": int, "O": int, "H": "recommendation"}}"""

    headers = {{"Authorization": f"Bearer {{api_key}}", "Content-Type": "application/json"}}
    payload = {{
        "model": "llama-3.3-70b-versatile",
        "messages": [{{"role": "user", "content": prompt}}],
        "max_tokens": 100,
        "temperature": 0.1
    }}

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                         json=payload, headers=headers, timeout=30)
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
        print(f"    [WARN] Groq call failed: {{e}}")
        return None

def needs_scoring(row):
    """Return True if L, M, N, or O are blank."""
    for col_idx in [COL["scarcity"]-1, COL["liquidity"]-1, COL["mascot"]-1, COL["depth"]-1]:
        if col_idx < len(row) and not str(row[col_idx]).strip():
            return True
    return False

# ── Conditional formatting ────────────────────────────────────────────────────
def apply_conditional_formatting(ws, sh, all_rows):
    sheet_id = ws.id
    requests_batch = []

    for i, row in enumerate(all_rows[1:], start=2):
        def col_val(col_key):
            idx = COL[col_key] - 1
            v = row[idx] if idx < len(row) else ""
            return str(v).strip()

        # Box % — col G
        try:
            g_raw = col_val("box_pct").replace("%", "")
            g_val = float(g_raw)
            if g_val > 1.0:   # already a ratio not percentage
                pass
            else:
                g_val = g_val  # it's already 0.x ratio
            if g_val > 1.0:
                color = {"red": 1.0, "green": 0.0, "blue": 0.0}
            elif g_val >= 0.9:
                color = {"red": 1.0, "green": 0.6, "blue": 0.0}
            elif g_val >= 0.75:
                color = {"red": 1.0, "green": 1.0, "blue": 0.0}
            else:
                color = {"red": 0.0, "green": 0.7, "blue": 0.0}
            requests_batch.append(_cell_color(sheet_id, i-1, COL["box_pct"]-1, color))
        except (ValueError, TypeError):
            pass

        # Chase % — col I
        try:
            i_val = float(col_val("chase_pct").replace("%", ""))
            color = {"red": 1.0, "green": 0.0, "blue": 0.0} if i_val > 0.5 else {"red": 0.0, "green": 0.7, "blue": 0.0}
            requests_batch.append(_cell_color(sheet_id, i-1, COL["chase_pct"]-1, color))
        except (ValueError, TypeError):
            pass

        # Decision score — col K
        try:
            k_val = int(float(col_val("decision")))
            if k_val >= 16:
                color = {"red": 0.0, "green": 0.39, "blue": 0.0}
            elif k_val >= 12:
                color = {"red": 0.57, "green": 0.82, "blue": 0.31}
            elif k_val >= 8:
                color = {"red": 1.0, "green": 1.0, "blue": 0.0}
            elif k_val >= 4:
                color = {"red": 1.0, "green": 0.6, "blue": 0.0}
            else:
                color = {"red": 1.0, "green": 0.0, "blue": 0.0}
            requests_batch.append(_cell_color(sheet_id, i-1, COL["decision"]-1, color))
        except (ValueError, TypeError):
            pass

        # Date col B — age based colouring
        try:
            date_str = col_val("date")
            print_status = col_val("print_status").lower()
            if date_str and "in print" not in print_status:
                dt = datetime.datetime.strptime(date_str, "%b-%y")
                today = date.today()
                months_ago = (today.year - dt.year) * 12 + (today.month - dt.month)
                if months_ago > 24:
                    requests_batch.append(_cell_color(sheet_id, i-1, COL["date"]-1, {"red": 1.0, "green": 0.0, "blue": 0.0}))
                elif months_ago >= 18:
                    requests_batch.append(_cell_color(sheet_id, i-1, COL["date"]-1, {"red": 1.0, "green": 1.0, "blue": 0.0}))
        except (ValueError, TypeError):
            pass

    # Send in batches of 50
    for i in range(0, len(requests_batch), 50):
        try:
            sh.batch_update({"requests": requests_batch[i:i+50]})
            time.sleep(1)  # avoid quota
        except Exception as e:
            print(f"  [WARN] Formatting batch failed: {e}")

def _cell_color(sheet_id, row_idx, col_idx, color):
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row_idx,
                "endRowIndex": row_idx + 1,
                "startColumnIndex": col_idx,
                "endColumnIndex": col_idx + 1
            },
            "cell": {"userEnteredFormat": {"backgroundColor": color}},
            "fields": "userEnteredFormat.backgroundColor"
        }
    }

# ── Save local copies ─────────────────────────────────────────────────────────
def save_local_copies(sh, gc):
    # Google Sheets is the source of truth — local copy is optional convenience only
    pass

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    today = date.today()
    print(f"=== Pokemon Tracker v2 === {today} ===")

    print("\n[1/8] Connecting to Google Sheets ...")
    sh, config, gc = connect_sheets()
    print(f"  Connected: {sh.title}")

    print("\n[2/8] Backing up ...")
    backup_sheet(sh, gc)

    print("\n[3/8] Setting up monthly sheet ...")
    ws = get_or_create_monthly_sheet(sh)

    rate = get_usd_to_gbp()
    print(f"\n  USD->GBP rate: {rate:.4f}")

    print("\n[4/8] Fetching price data ...")
    dawnglare = fetch_dawnglare_prices()
    wizard_index = fetch_wizard_index()

    print(f"\n[5/8] Checking for new sets (last {NEW_SET_DAYS} days) ...")
    new_sets = detect_new_sets(ws, wizard_index)
    if new_sets:
        print(f"  Found {len(new_sets)} new sets: {[s['name'] for s in new_sets]}")
        for entry in new_sets:
            era, _ = fetch_wizard_set_details(entry["url"])
            new_row = [""] * 15
            new_row[COL["era"]-1] = era or ""
            new_row[COL["date"]-1] = entry.get("date_str", "")
            new_row[COL["name"]-1] = entry["name"]
            ws.append_row(new_row)
            print(f"    Added: {entry['name']} | Era: {era} | Date: {entry.get('date_str','')}")
    else:
        print("  No new sets found")

    print("\n[6/8] Updating prices ...")
    all_rows = ws.get_all_values()
    updates = []
    gemini_queue = []

    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) < 3 or not row[2].strip():
            continue

        set_name = row[2].strip()
        print(f"\n  Row {i}: {set_name}")

        # Column D
        usd_price, note = find_booster_box_price(set_name, dawnglare)
        gbp = None
        if usd_price is not None:
            gbp = round(usd_price * rate, 2)
            updates.append((i, COL["bb_price"], gbp))
            print(f"    D: £{gbp:.2f} [{note}]")
        else:
            print(f"    D: NOT FOUND")

        # Columns E & F
        wizard_entry = find_wizard_entry(set_name, wizard_index)
        set_value_gbp = None
        top3_usd_sum = None
        chase_str = None
        if wizard_entry:
            set_value_gbp, chase_str, top3_usd_sum = fetch_wizard_set_page(wizard_entry["url"], rate)
            if set_value_gbp is not None:
                updates.append((i, COL["set_value"], set_value_gbp))
                print(f"    E: £{set_value_gbp:.2f}")
            if chase_str:
                updates.append((i, COL["chase"], chase_str))
                print(f"    F: {chase_str}")
        else:
            print(f"    E/F: no Wizard match")

        # Column G — Box % (D/E)
        box_pct = None
        if gbp and set_value_gbp and set_value_gbp > 0:
            box_pct = round(gbp / set_value_gbp, 4)
            updates.append((i, COL["box_pct"], box_pct))
            print(f"    G: {box_pct:.1%}")

        # Column I — Chase % (top3/set_value)
        chase_pct = None
        if top3_usd_sum and set_value_gbp and set_value_gbp > 0:
            top3_gbp = round(top3_usd_sum * rate, 2)
            chase_pct = round(top3_gbp / set_value_gbp, 4)
            updates.append((i, COL["chase_pct"], chase_pct))
            print(f"    I: {chase_pct:.1%}")

        # Queue for Gemini if unscored
        if needs_scoring(row):
            gemini_queue.append({
                "row_idx": i,
                "name": set_name,
                "era": row[COL["era"]-1] if len(row) > COL["era"]-1 else "",
                "date": row[COL["date"]-1] if len(row) > COL["date"]-1 else "",
                "bb_price": gbp,
                "set_value": set_value_gbp,
                "chase": chase_str or "",
                "box_pct": f"{box_pct:.1%}" if box_pct else "",
                "chase_pct": f"{chase_pct:.1%}" if chase_pct else "",
                "print_status": row[COL["print_status"]-1] if len(row) > COL["print_status"]-1 else "",
            })

    # Write price updates in batches
    print(f"\n  Writing {len(updates)} cell updates ...")
    try:
        for batch_start in range(0, len(updates), 200):
            batch = updates[batch_start:batch_start+200]
            cell_list = [gspread.Cell(r, c, v) for r, c, v in batch]
            ws.update_cells(cell_list, value_input_option='USER_ENTERED')
            time.sleep(2)
        print("  Price updates written")
    except Exception as e:
        print(f"  [ERROR] Failed to write updates: {e}")

    # Gemini scoring with rate limiting
    print(f"\n[7/8] Gemini scoring ({len(gemini_queue)} sets to score) ...")
    gemini_updates = []
    for idx, item in enumerate(gemini_queue):
        print(f"  [{idx+1}/{len(gemini_queue)}] Scoring: {item['name']} ...")
        result = call_gemini(item)
        if result:
            row_idx = item["row_idx"]
            k = result["L"] + result["M"] + result["N"] + result["O"]
            gemini_updates.extend([
                gspread.Cell(row_idx, COL["recommendation"], result["H"]),
                gspread.Cell(row_idx, COL["scarcity"], result["L"]),
                gspread.Cell(row_idx, COL["liquidity"], result["M"]),
                gspread.Cell(row_idx, COL["mascot"], result["N"]),
                gspread.Cell(row_idx, COL["depth"], result["O"]),
                gspread.Cell(row_idx, COL["decision"], k),
            ])
            print(f"    H={result['H']} L={result['L']} M={result['M']} N={result['N']} O={result['O']} K={k}")
        time.sleep(1)  # Groq is fast, small delay is polite

        # Write every 10 scores to avoid losing progress
        if len(gemini_updates) >= 60:
            try:
                ws.update_cells(gemini_updates)
                gemini_updates = []
                time.sleep(2)
            except Exception as e:
                print(f"  [WARN] Gemini batch write failed: {e}")

    if gemini_updates:
        try:
            ws.update_cells(gemini_updates)
        except Exception as e:
            print(f"  [WARN] Final Gemini write failed: {e}")

    print(f"  Gemini scoring complete")

    # Conditional formatting
    print("\n  Applying conditional formatting ...")
    all_rows = ws.get_all_values()
    apply_conditional_formatting(ws, sh, all_rows)

    print("\n[8/8] Saving local copies ...")
    save_local_copies(sh, gc)

    print(f"\n{'='*50}")
    print(f"Done!")
    print(f"  New sets added: {len(new_sets)}")
    print(f"  Price updates: {len(updates)} cells")
    print(f"  Gemini scores: {len(gemini_queue)} sets")

if __name__ == "__main__":
    main()
