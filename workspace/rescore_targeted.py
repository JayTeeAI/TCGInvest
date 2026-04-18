#!/usr/bin/env python3
"""
Targeted re-score script — corrected investment rubric
Only re-scores sets that are obviously wrong based on box % vs recommendation.
Writes corrected scores back to SQLite for the April 2026 run date.

Run:
  cd /root/.openclaw/workspace && source venv/bin/activate
  python rescore_targeted.py
"""

import sqlite3
import os
import re
import json
import time
import requests

DB_PATH    = "/root/.openclaw/db/tracker.db"
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
RUN_DATE   = "2026-04-01"

# Sets to re-score — identified as clearly wrong
TARGET_SETS = [
    "Celebrations 25th",
    "Champions Path",
    "Rebel Clash",
    "Sword and Shield",
    "Team Up",
    "Darkness Ablaze",
    "151",
    "Cosmic Eclipse",
    "Unified Minds",
]

VALID_RECOMMENDATIONS = {
    "Strong Buy", "Buy", "Accumulate", "Hold", "Reduce", "Sell", "Overvalued"
}


def call_groq(set_data: dict) -> dict | None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("  [ERROR] No GROQ_API_KEY found")
        return None

    box_pct_display = ""
    if set_data.get("box_pct"):
        box_pct_display = f"{set_data['box_pct'] * 100:.1f}%"

    prompt = f"""You are a Pokemon TCG sealed product investment analyst.
Score this set and provide a recommendation based strictly on the rules below.

Set: {set_data.get('name', '')}
Release Date: {set_data.get('date_released', 'Unknown')}
Era: {set_data.get('era', 'Unknown')}
BB Price (GBP): {set_data.get('bb_price_gbp', 'Unknown')}
Set Value (GBP): {set_data.get('set_value_gbp', 'Unknown')}
Box % of Set Value: {box_pct_display}
Top 3 Chase Cards: {set_data.get('top3_chase', 'Unknown')}
Chase Card %: {set_data.get('chase_pct', 'Unknown')}
Print Status: {set_data.get('print_status', 'Unknown')}

=== RECOMMENDATION RULES (follow exactly, no exceptions) ===

OVERVALUED or SELL — apply when:
- Box % is over 100% (box costs MORE than the cards inside)
- Use OVERVALUED if still in print
- Use SELL if out of print but box % still over 100%
- NO exceptions. A set with box % > 100% can NEVER be Buy, Strong Buy or Accumulate.

REDUCE — apply when:
- Box % is 85–100% and OOP 4+ years (fully priced in, opportunity passed)

HOLD — apply when:
- Box % is 75–100% and OOP 2–4 years
- OR box % is 75–85% and OOP 4+ years

ACCUMULATE — apply when:
- Set is still in print but approaching end of print run (within ~12 months)
- OR box % is 60–75% and OOP 2–4 years with decent mascot

BUY — apply when:
- Box % is 50–75%
- AND out of print within the last 2 years
- AND decent mascot (Charizard, Pikachu, Eevee, Umbreon or similar popular Pokemon)

STRONG BUY — apply when ALL FOUR are true:
- Box % is under 50%
- Out of print within the last 2 years
- Strong mascot (Charizard/Eevee/Umbreon as PRIMARY chase)
- Deep set (many valuable cards, not just 1-2 chase cards)

=== SCORING (integer 1-5 each) ===

L Scarcity:
5 = OOP within 2 years, price still forming
4 = OOP 2-4 years, some upside
3 = OOP 4+ years, fully priced in
2 = Still printing, approaching OOP within 12 months
1 = In print, heavily available

M Liquidity:
5 = Booster Box, fast sell
3 = Mixed products
1 = Slow sell, niche demand

N Mascot Power:
5 = Charizard/Eevee/Umbreon as PRIMARY chase
4 = Strong mascot as secondary chase
3 = Popular but not top tier
2 = Niche Pokemon
1 = No recognisable chase cards

O Set Depth:
5 = Many Illustration Rares, multiple chase tiers
3 = Several good cards
1 = Only 1-2 good cards

Respond in JSON only, no other text:
{{"L": int, "M": int, "N": int, "O": int, "H": "recommendation"}}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 120,
        "temperature": 0.0,
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
        print(f"  [WARN] Groq call failed: {e}")
        return None


def main():
    print(f"=== Targeted Re-score === run_date={RUN_DATE} ===\n")
    print(f"Targeting {len(TARGET_SETS)} sets\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    for set_name in TARGET_SETS:
        print(f"[{set_name}]")

        # Fetch current data
        row = cur.execute("""
            SELECT
                s.id, s.name, s.era, s.date_released, s.print_status,
                m.bb_price_gbp, m.set_value_gbp, m.top3_chase,
                m.box_pct, m.chase_pct,
                sc.recommendation, sc.decision_score,
                sc.scarcity, sc.liquidity, sc.mascot_power, sc.set_depth
            FROM sets s
            JOIN monthly_snapshots m ON m.set_id = s.id AND m.run_date = ?
            LEFT JOIN scores sc ON sc.set_id = s.id AND sc.run_date = ?
            WHERE s.name = ?
        """, (RUN_DATE, RUN_DATE, set_name)).fetchone()

        if not row:
            print(f"  [SKIP] Not found in DB for {RUN_DATE}\n")
            continue

        r = dict(row)
        box_pct_display = f"{r['box_pct'] * 100:.1f}%" if r['box_pct'] else "?"
        print(f"  Current: box%={box_pct_display} rec={r['recommendation']} score={r['decision_score']}")

        result = call_groq(r)
        if not result:
            print(f"  [SKIP] Groq failed\n")
            continue

        k = result["L"] + result["M"] + result["N"] + result["O"]
        print(f"  New:     H={result['H']} L={result['L']} M={result['M']} N={result['N']} O={result['O']} K={k}")

        # Write to DB
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
        """, (r["id"], RUN_DATE, result["H"], result["L"], result["M"], result["N"], result["O"], k))

        conn.commit()
        print(f"  Saved.\n")
        time.sleep(2)

    conn.close()

    print("=" * 50)
    print("Re-score complete. Verify with:")
    print(f'sqlite3 {DB_PATH} "SELECT s.name, m.box_pct*100, sc.recommendation, sc.decision_score FROM sets s JOIN monthly_snapshots m ON m.set_id=s.id AND m.run_date=\'{RUN_DATE}\' JOIN scores sc ON sc.set_id=s.id AND sc.run_date=\'{RUN_DATE}\' WHERE s.name IN (\'151\',\'Champions Path\',\'Celebrations 25th\') ORDER BY m.box_pct DESC;"')


if __name__ == "__main__":
    main()
