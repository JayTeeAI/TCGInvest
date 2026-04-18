#!/usr/bin/env python3
"""
Standalone Groq scoring script.
Scores only unscored sets with no rate limit issues.
"""
import os, json, re, time
import requests
import gspread
from google.oauth2.service_account import Credentials

CONFIG_FILE      = "/root/.openclaw/workspace/config.json"
CREDENTIALS_FILE = "/root/.openclaw/workspace/google-credentials.json"
GROQ_URL         = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL       = "llama-3.3-70b-versatile"

COL = {
    "era": 1, "date": 2, "name": 3, "bb_price": 4, "set_value": 5,
    "chase": 6, "box_pct": 7, "recommendation": 8, "chase_pct": 9,
    "print_status": 10, "decision": 11, "scarcity": 12,
    "liquidity": 13, "mascot": 14, "depth": 15
}

VALID = {"Strong Buy", "Buy", "Accumulate", "Hold", "Reduce", "Sell", "Overvalued"}

def connect():
    scopes = ["https://spreadsheets.google.com/feeds",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    gc = gspread.authorize(creds)
    config = json.load(open(CONFIG_FILE))
    sh = gc.open_by_key(config["sheet_id"])
    return sh

def call_groq(data):
    api_key = os.environ.get("GROQ_API_KEY")
    prompt = f"""You are a Pokemon TCG investment analyst. Score this set and provide a recommendation.

Set: {data['name']}
Era: {data['era']}
Release Date: {data['date']}
BB Price (GBP): {data['bb_price']}
Set Value (GBP): {data['set_value']}
Top 3 Chase Cards: {data['chase']}
Box %: {data['box_pct']}
Chase Card %: {data['chase_pct']}
Print Status: {data['print_status']}

Score each as integer 1-5:
L Scarcity: 5=Out of Print, 4=Going OOP soon 18-24mo, 3=18mo old still printing, 2=In print under 18mo, 1=Heavily restocked
M Liquidity: 5=Booster Box fast sell, 3=Mixed products, 1=Collection box slow sell
N Mascot Power: 5=Charizard/Eevee/Umbreon top chase, 3=Popular not top tier, 1=No big chase cards
O Set Depth: 5=Many Illustration Rares spread across set, 3=Several good cards, 1=Only 1-2 good cards

H must be exactly one of: Strong Buy, Buy, Accumulate, Hold, Reduce, Sell, Overvalued

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
        if result.get("H") not in VALID:
            result["H"] = "Hold"
        return result
    except Exception as e:
        print(f"    [ERROR] {e}")
        return None

def main():
    print("=== Groq Scorer ===")
    sh = connect()
    ws = sh.worksheets()[0]
    print(f"  Sheet: {ws.title}")

    all_rows = ws.get_all_values()
    to_score = []

    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) < 3 or not row[2].strip():
            continue
        l = row[COL["scarcity"]-1] if len(row) > COL["scarcity"]-1 else ""
        m = row[COL["liquidity"]-1] if len(row) > COL["liquidity"]-1 else ""
        n = row[COL["mascot"]-1] if len(row) > COL["mascot"]-1 else ""
        o = row[COL["depth"]-1] if len(row) > COL["depth"]-1 else ""
        if not (str(l).strip() and str(m).strip() and str(n).strip() and str(o).strip()):
            to_score.append((i, row))

    print(f"  Sets to score: {len(to_score)}")
    if not to_score:
        print("  All sets already scored!")
        return

    for idx, (row_idx, row) in enumerate(to_score):
        name = row[COL["name"]-1]
        print(f"\n  [{idx+1}/{len(to_score)}] {name} ...")

        data = {k: (row[v-1] if len(row) > v-1 else "") for k, v in COL.items()}
        data["name"] = name

        result = call_groq(data)
        if result:
            k = result["L"] + result["M"] + result["N"] + result["O"]
            print(f"    H={result['H']} L={result['L']} M={result['M']} N={result['N']} O={result['O']} K={k}")
            try:
                ws.update_cells([
                    gspread.Cell(row_idx, COL["recommendation"], result["H"]),
                    gspread.Cell(row_idx, COL["scarcity"], result["L"]),
                    gspread.Cell(row_idx, COL["liquidity"], result["M"]),
                    gspread.Cell(row_idx, COL["mascot"], result["N"]),
                    gspread.Cell(row_idx, COL["depth"], result["O"]),
                    gspread.Cell(row_idx, COL["decision"], k),
                ])
                print(f"    Saved")
            except Exception as e:
                print(f"    [WARN] Save failed: {e}")
        else:
            print(f"    Skipped")

        time.sleep(1)  # Groq is generous but small delay is polite

    print(f"\n=== Done! ===")

if __name__ == "__main__":
    main()
