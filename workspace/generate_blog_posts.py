#!/usr/bin/env python3
"""
TCGInvest Blog Post Auto-Generator — v3
Weekly cadence (Thu 11:00 via cron). Fully decoupled from first_run_v3.py.
Reads monthly_snapshots, scores, chase_card_prices directly via psycopg2.
Writes all posts to blog_posts table (slug-based upsert).
Legacy TSX movers component still generated for existing /blog/[slug] routing.

Usage:
  python3 generate_blog_posts.py                    # full weekly run
  python3 generate_blog_posts.py --pillar movers
  python3 generate_blog_posts.py --pillar set_guide --set-id 12
  python3 generate_blog_posts.py --pillar chase_deepdive --card-id 5
  python3 generate_blog_posts.py --pillar era_guide --era "SWSH"
  python3 generate_blog_posts.py --pillar sealed_vs_singles --set-id 12
  python3 generate_blog_posts.py --pillar price_trend
  python3 generate_blog_posts.py --all-sets          # regenerate all set guides
  python3 generate_blog_posts.py --all-cards         # regenerate all chase deepdives
  python3 generate_blog_posts.py --all-eras          # regenerate all era guides
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import subprocess
from datetime import datetime, date
from pathlib import Path
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv("/root/.openclaw/api/.env")

API_KEY      = os.getenv("API_KEY", "")
API_BASE     = "http://127.0.0.1:8000"
DATABASE_URL = os.getenv("DATABASE_URL", "")
POSTS_LIB    = "/root/.openclaw/frontend/lib/blog/posts.ts"
COMPONENTS_DIR = "/root/.openclaw/frontend/components/blog"
FRONTEND_DIR = "/root/.openclaw/frontend"


# ── DB connection ─────────────────────────────────────────────────────────────

def get_db_conn():
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(name):
    s = name.lower().replace("s&v", "sandv").replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def fmt_gbp(v):
    if v is None:
        return "N/A"
    return f"£{float(v):,.2f}"

def fmt_pct(v):
    if v is None:
        return "N/A"
    return f"{float(v):.1f}%"

def read_time_estimate(md: str) -> int:
    words = len(md.split())
    return max(3, round(words / 200))

def api_get(path):
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"X-API-Key": API_KEY}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def month_label(date_str):
    dt = datetime.strptime(str(date_str), "%Y-%m-%d")
    return dt.strftime("%B %Y")


# ── DB writer ─────────────────────────────────────────────────────────────────

def upsert_blog_post(conn, slug, title, description, category, content_md, featured=False, published=True):
    """Insert or update a post in blog_posts. Slug is the conflict key."""
    cur = conn.cursor()
    read_time = read_time_estimate(content_md)
    today = date.today()
    cur.execute("""
        INSERT INTO blog_posts (slug, title, description, category, date, content_md, read_time, featured, published)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (slug) DO UPDATE SET
            title       = EXCLUDED.title,
            description = EXCLUDED.description,
            content_md  = EXCLUDED.content_md,
            read_time   = EXCLUDED.read_time,
            featured    = EXCLUDED.featured,
            updated_at  = NOW()
    """, (slug, title, description, category, today, content_md, read_time, featured, published))
    conn.commit()
    print(f"  ✓ upserted: {slug}")


# ── Movers data (direct DB read — decoupled from API) ─────────────────────────

def get_movers_from_db(conn):
    """
    Read the two most recent run_dates from monthly_snapshots and compute movers.
    Returns (gainers, drops, latest_date, previous_date) or (None,None,None,None).
    """
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT run_date FROM monthly_snapshots ORDER BY run_date DESC LIMIT 2")
    rows = cur.fetchall()
    if len(rows) < 2:
        print("Not enough run_dates for movers")
        return None, None, None, None
    latest, previous = str(rows[0][0]), str(rows[1][0])

    cur.execute("""
        SELECT
            s.id, s.name, s.era,
            ms_curr.bb_price_gbp  AS curr_bb,
            ms_prev.bb_price_gbp  AS prev_bb,
            ms_curr.set_value_gbp AS curr_sv,
            ms_curr.box_pct       AS curr_box_pct,
            sc.recommendation     AS rec,
            sc.decision_score     AS score
        FROM sets s
        JOIN monthly_snapshots ms_curr ON ms_curr.set_id = s.id AND ms_curr.run_date = %s
        JOIN monthly_snapshots ms_prev ON ms_prev.set_id = s.id AND ms_prev.run_date = %s
        LEFT JOIN scores sc ON sc.set_id = s.id AND sc.run_date = %s
        WHERE ms_curr.bb_price_gbp IS NOT NULL AND ms_prev.bb_price_gbp IS NOT NULL
    """, (latest, previous, latest))

    movers = []
    for row in cur.fetchall():
        set_id, name, era, curr, prev, sv, box_pct, rec, score = row
        curr, prev = float(curr), float(prev)
        pct = round((curr - prev) / prev * 100, 1) if prev else None
        movers.append({
            "set_id": set_id, "name": name, "era": era,
            "curr_bb": curr, "prev_bb": prev, "set_value": float(sv) if sv else None,
            "box_pct": float(box_pct) if box_pct else None,
            "pct_change": pct, "rec": rec, "score": score
        })

    gainers = sorted([m for m in movers if m["pct_change"] and m["pct_change"] > 0],
                     key=lambda x: -x["pct_change"])[:5]
    drops   = sorted([m for m in movers if m["pct_change"] and m["pct_change"] < 0],
                     key=lambda x: x["pct_change"])[:5]
    return gainers, drops, latest, previous


# ── PILLAR 1: Movers (legacy TSX + DB write) ───────────────────────────────────

def generate_movers_post(conn):
    gainers, drops, latest, previous = get_movers_from_db(conn)
    if not gainers:
        print("Movers: insufficient data — skipping")
        return

    today = date.today()
    month_str = today.strftime("%B %Y").lower().replace(" ", "-")
    slug  = f"pokemon-booster-box-movers-{month_str}"
    title = f"Pokemon TCG Booster Box Price Movers — {today.strftime('%B %Y')}"
    desc  = (f"{gainers[0]['name']} up {gainers[0]['pct_change']}%, "
             f"{drops[0]['name']} drops {abs(drops[0]['pct_change'])}%. "
             f"This month's biggest sealed product price movements across tracked sets.")

    # Build markdown content for DB
    md = f"""# {title}

*{month_label(previous)} vs {month_label(latest)} — prices from eBay UK sold listings via TCGInvest monthly pipeline.*

## Overview

Booster box prices tracked across {len(gainers) + len(drops)}+ sets this month.
Data sourced from eBay UK sold listings. AI scores powered by Groq llama-3.3-70b.

## 🚀 Biggest Gainers

| Set | Era | Prev | Curr | Change | Rating |
|-----|-----|------|------|--------|--------|
"""
    for m in gainers:
        md += f"| [{m['name']}](/sets/{slugify(m['name'])}) | {m['era']} | {fmt_gbp(m['prev_bb'])} | {fmt_gbp(m['curr_bb'])} | **+{m['pct_change']}%** | {m['rec'] or 'N/A'} |\n"

    md += f"""
## 📉 Biggest Drops

| Set | Era | Prev | Curr | Change | Rating |
|-----|-----|------|------|--------|--------|
"""
    for m in drops:
        md += f"| [{m['name']}](/sets/{slugify(m['name'])}) | {m['era']} | {fmt_gbp(m['prev_bb'])} | {fmt_gbp(m['curr_bb'])} | **{m['pct_change']}%** | {m['rec'] or 'N/A'} |\n"

    md += f"""
## What's Driving These Moves?

The biggest gainers this month are led by **{gainers[0]['name']}** ({gainers[0]['era']}),
up {gainers[0]['pct_change']}% to {fmt_gbp(gainers[0]['curr_bb'])}. This reflects continued
strong demand for sealed product in this era.

On the downside, **{drops[0]['name']}** saw the sharpest correction at {drops[0]['pct_change']}%,
suggesting short-term profit-taking or increased supply.

*Track live prices and AI investment scores for all {len(gainers) + len(drops)}+ sets on the
[Booster Box Tracker](/tools/tracker).*

---
*Comparison period: {month_label(previous)} → {month_label(latest)}. Next update: following weekly pipeline run.*
"""

    upsert_blog_post(conn, slug, title, desc, "movers", md, featured=True)

    # Also write legacy TSX component for backward-compat routing
    _write_legacy_movers_tsx(gainers, drops, latest, previous, slug, title, desc, today)


def _write_legacy_movers_tsx(gainers, drops, latest, previous, slug, title, desc, today):
    """Write the TSX component + update posts.ts + router + sitemap (existing pattern)."""
    def gain_row(m):
        slug_ = slugify(m["name"])
        return f'''          <GainRow name="{m['name']}" slug="{slug_}" prev={{{m['prev_bb']}}} curr={{{m['curr_bb']}}} pct={{{m['pct_change']}}} rec="{m['rec'] or 'N/A'}" />'''

    def drop_row(m):
        slug_ = slugify(m["name"])
        return f'''          <DropRow name="{m['name']}" slug="{slug_}" prev={{{m['prev_bb']}}} curr={{{m['curr_bb']}}} pct={{{m['pct_change']}}} rec="{m['rec'] or 'N/A'}" />'''

    gainer_rows = "\n".join(gain_row(m) for m in gainers)
    drop_rows   = "\n".join(drop_row(m) for m in drops)
    comp_name   = f"MoverPost{today.strftime('%b%Y')}Content"
    comp_file   = f"{COMPONENTS_DIR}/MoverPost{today.strftime('%b%Y')}Content.tsx"

    component = f'''\
import Link from "next/link"

function GainRow({{ name, slug, prev, curr, pct, rec }}: {{ name: string; slug: string; prev: number; curr: number; pct: number; rec: string }}) {{
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-800 last:border-0">
      <div>
        <Link href={{`/sets/${{slug}}`}} className="text-white font-medium text-sm hover:text-blue-400 transition-colors">{{name}}</Link>
        <p className="text-slate-500 text-xs mt-0.5">{{rec}}</p>
      </div>
      <div className="text-right">
        <p className="text-emerald-400 font-bold text-sm">+{{pct}}%</p>
        <p className="text-slate-500 text-xs">£{{prev.toLocaleString()}} &rarr; £{{curr.toLocaleString()}}</p>
      </div>
    </div>
  )
}}

function DropRow({{ name, slug, prev, curr, pct, rec }}: {{ name: string; slug: string; prev: number; curr: number; pct: number; rec: string }}) {{
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-800 last:border-0">
      <div>
        <Link href={{`/sets/${{slug}}`}} className="text-white font-medium text-sm hover:text-blue-400 transition-colors">{{name}}</Link>
        <p className="text-slate-500 text-xs mt-0.5">{{rec}}</p>
      </div>
      <div className="text-right">
        <p className="text-red-400 font-bold text-sm">{{pct}}%</p>
        <p className="text-slate-500 text-xs">£{{prev.toLocaleString()}} &rarr; £{{curr.toLocaleString()}}</p>
      </div>
    </div>
  )
}}

export function {comp_name}() {{
  return (
    <div>
      <div className="mb-8">
        <h2 className="text-xl font-bold text-white mb-4">Overview</h2>
        <p className="text-slate-300 leading-relaxed mb-4">
          {month_label(latest)} vs {month_label(previous)} comparison across tracked booster box sets.
          Data sourced from eBay UK sold listings via TCGInvest monthly price pipeline.
        </p>
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-bold text-white mb-4">&#x1F680; Biggest Gainers</h2>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
{gainer_rows}
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-bold text-white mb-4">&#x1F4C9; Biggest Drops</h2>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
{drop_rows}
        </div>
      </div>

      <p className="text-slate-500 text-xs mt-6">
        Comparison period: {month_label(previous)} vs {month_label(latest)}.
        Prices from eBay UK sold listings. AI scores via Groq llama-3.3-70b.
        Next update: following weekly pipeline run.
      </p>
    </div>
  )
}}
'''

    with open(comp_file, "w") as f:
        f.write(component)
    print(f"  ✓ TSX component: {comp_file}")

    # Update posts.ts registry
    with open(POSTS_LIB, "r") as f:
        src = f.read()
    if slug not in src:
        post_date = date.today().strftime("%Y-%m-%d")
        new_entry = f'''  {{
    slug: "{slug}",
    title: "{title}",
    description: "{desc}",
    date: "{post_date}",
    category: "movers",
    readTime: 4,
    featured: true,
  }},'''
        src = src.replace("export const posts: BlogPost[] = [",
                          f"export const posts: BlogPost[] = [\n{new_entry}")
        with open(POSTS_LIB, "w") as f:
            f.write(src)
        print(f"  ✓ posts.ts updated: {slug}")

    # Update blog router
    router_path = f"{FRONTEND_DIR}/app/blog/[slug]/page.tsx"
    with open(router_path, "r") as f:
        src = f.read()
    import_line = f'import {{ {comp_name} }} from "@/components/blog/{comp_name}"'
    if comp_name not in src:
        src = src.replace(
            'import { MoverPostContent }',
            f'{import_line}\nimport {{ MoverPostContent }}'
        )
        src = src.replace(
            '{slug === "pokemon-booster-box-movers-april-2026"',
            f'{{slug === "{slug}" && <{comp_name} />}}\n        {{slug === "pokemon-booster-box-movers-april-2026"'
        )
        with open(router_path, "w") as f:
            f.write(src)
        print(f"  ✓ blog router updated")

    # Update sitemap
    sitemap_path = f"{FRONTEND_DIR}/app/sitemap.ts"
    with open(sitemap_path, "r") as f:
        src = f.read()
    if slug not in src:
        new_entry = f'''    {{
      url: `${{baseUrl}}/blog/{slug}`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.85,
    }},'''
        marker = '    {\n      url: `${baseUrl}/blog/pokemon-booster-box-movers-april-2026`,'
        if marker in src:
            src = src.replace(marker, new_entry + "\n" + marker)
            with open(sitemap_path, "w") as f:
                f.write(src)
            print(f"  ✓ sitemap updated")


# ── PILLAR 2: Monthly Price Trend Report ──────────────────────────────────────

def generate_price_trend_report(conn):
    """
    Pillar 2: Monthly price trend report — market-wide view.
    Slug: pokemon-tcg-price-trends-MONTH-YEAR (monthly, one per run).
    """
    gainers, drops, latest, previous = get_movers_from_db(conn)
    if not gainers:
        print("Price trend: insufficient data — skipping")
        return

    today = date.today()
    month_str = today.strftime("%B-%Y").lower()
    slug  = f"pokemon-tcg-price-trends-{month_str}"
    title = f"Pokémon TCG Price Trends — {today.strftime('%B %Y')}"
    desc  = (f"Full market analysis of Pokémon TCG sealed product prices for {today.strftime('%B %Y')}. "
             f"Which sets are rising, which are cooling — data from {len(gainers)+len(drops)} tracked sets.")

    # Get full movers list for market stats
    cur = conn.cursor()
    cur.execute("""
        SELECT
            s.name, s.era,
            ms_curr.bb_price_gbp, ms_prev.bb_price_gbp,
            ms_curr.box_pct
        FROM sets s
        JOIN monthly_snapshots ms_curr ON ms_curr.set_id = s.id AND ms_curr.run_date = %s
        JOIN monthly_snapshots ms_prev ON ms_prev.set_id = s.id AND ms_prev.run_date = %s
        WHERE ms_curr.bb_price_gbp IS NOT NULL AND ms_prev.bb_price_gbp IS NOT NULL
    """, (latest, previous))
    all_sets = cur.fetchall()

    rising = sum(1 for r in all_sets if float(r[2]) > float(r[3]))
    falling = sum(1 for r in all_sets if float(r[2]) < float(r[3]))
    flat = len(all_sets) - rising - falling

    avg_curr = sum(float(r[2]) for r in all_sets) / len(all_sets) if all_sets else 0
    avg_prev = sum(float(r[3]) for r in all_sets) / len(all_sets) if all_sets else 0
    market_pct = round((avg_curr - avg_prev) / avg_prev * 100, 1) if avg_prev else 0

    # Era breakdown — avg box_pct by era
    cur.execute("""
        SELECT s.era, AVG(ms.box_pct), COUNT(*)
        FROM monthly_snapshots ms
        JOIN sets s ON s.id = ms.set_id
        WHERE ms.run_date = %s AND ms.box_pct IS NOT NULL
        GROUP BY s.era ORDER BY AVG(ms.box_pct) DESC
    """, (latest,))
    era_rows = cur.fetchall()

    md = f"""# {title}

*Data period: {month_label(previous)} → {month_label(latest)}. Source: eBay UK sold listings via TCGInvest pipeline.*

## Market Summary

The Pokémon TCG sealed market moved **{"up" if market_pct >= 0 else "down"} {abs(market_pct)}%** overall this month,
with **{rising} sets rising**, **{falling} sets falling**, and {flat} broadly flat.

Average booster box price across all tracked sets: **{fmt_gbp(avg_curr)}** (was {fmt_gbp(avg_prev)}).

## 🚀 Top 5 Gainers

| Set | Era | Change | Current Price |
|-----|-----|--------|---------------|
"""
    for m in gainers:
        md += f"| [{m['name']}](/sets/{slugify(m['name'])}) | {m['era']} | **+{m['pct_change']}%** | {fmt_gbp(m['curr_bb'])} |\n"

    md += f"""
## 📉 Top 5 Drops

| Set | Era | Change | Current Price |
|-----|-----|--------|---------------|
"""
    for m in drops:
        md += f"| [{m['name']}](/sets/{slugify(m['name'])}) | {m['era']} | **{m['pct_change']}%** | {fmt_gbp(m['curr_bb'])} |\n"

    if era_rows:
        md += "\n## Value Ratio by Era (Box Price vs Singles Value)\n\n"
        md += "*Box pct below 1.0 means sealed is cheaper than singles — potential upside.*\n\n"
        md += "| Era | Avg Box/Singles Ratio | Sets Tracked |\n|-----|----------------------|--------------|\n"
        for era, avg_bpct, count in era_rows:
            signal = "🟢 undervalued" if float(avg_bpct) < 0.8 else ("🔴 premium" if float(avg_bpct) > 1.2 else "🟡 fair")
            md += f"| {era} | {float(avg_bpct):.2f}x — {signal} | {count} |\n"

    md += f"""
## Key Takeaways

- **{"Rising" if market_pct >= 0 else "Falling"} market:** {abs(market_pct)}% average move this month
- **Strongest era by value ratio:** {era_rows[0][0] if era_rows else 'N/A'} (avg {float(era_rows[0][1]):.2f}x if era_rows else '')
- Most volatile set: **{gainers[0]['name']}** (+{gainers[0]['pct_change']}%)

*[Track live prices and AI scores →](/tools/tracker)*

---
*TCGInvest tracks {len(all_sets)} booster box sets with monthly price snapshots. Data from eBay UK sold listings.*
"""

    upsert_blog_post(conn, slug, title, desc, "analysis", md, featured=False)


# ── PILLAR 3: Set Investment Guide ────────────────────────────────────────────

def generate_set_investment_guide(conn, set_id=None, set_name=None):
    """
    Pillar 1: "Is [Set Name] worth buying in 2026?" — one per set.
    Slug: is-[set-slug]-worth-buying-2026
    """
    cur = conn.cursor()

    if set_id:
        cur.execute("SELECT id, name, era, print_status, date_released FROM sets WHERE id = %s", (set_id,))
    elif set_name:
        cur.execute("SELECT id, name, era, print_status, date_released FROM sets WHERE name ILIKE %s", (set_name,))
    else:
        return

    row = cur.fetchone()
    if not row:
        print(f"  Set not found: {set_id or set_name}")
        return

    sid, name, era, print_status, date_released = row

    # Price history (last 6 snapshots)
    cur.execute("""
        SELECT run_date, bb_price_gbp, set_value_gbp, box_pct
        FROM monthly_snapshots
        WHERE set_id = %s
        ORDER BY run_date DESC LIMIT 6
    """, (sid,))
    snapshots = cur.fetchall()

    if not snapshots:
        print(f"  No price data for {name} — skipping")
        return

    latest_snap = snapshots[0]
    curr_price  = float(latest_snap[1]) if latest_snap[1] else None
    curr_sv     = float(latest_snap[2]) if latest_snap[2] else None
    curr_bpct   = float(latest_snap[3]) if latest_snap[3] else None

    # AI score
    cur.execute("""
        SELECT recommendation, decision_score, scarcity, liquidity, mascot_power, set_depth
        FROM scores WHERE set_id = %s ORDER BY run_date DESC LIMIT 1
    """, (sid,))
    score_row = cur.fetchone()

    # Chase cards
    cur.execute("""
        SELECT cc.card_name, cc.rarity, ccp.raw_gbp, ccp.psa10_gbp
        FROM chase_cards cc
        LEFT JOIN chase_card_prices ccp ON ccp.chase_card_id = cc.id
        WHERE cc.set_id = %s
        ORDER BY ccp.raw_gbp DESC NULLS LAST, ccp.snapshot_date DESC NULLS LAST
    """, (sid,))
    chase_rows = cur.fetchall()
    # Deduplicate by card name (keep highest price row)
    seen = {}
    for r in chase_rows:
        if r[0] not in seen:
            seen[r[0]] = r
    chase_cards = list(seen.values())[:5]

    # Price trend (6-month direction)
    if len(snapshots) >= 2:
        oldest = float(snapshots[-1][1]) if snapshots[-1][1] else None
        trend_pct = round((curr_price - oldest) / oldest * 100, 1) if (curr_price and oldest) else None
    else:
        trend_pct = None

    set_slug  = slugify(name)
    slug      = f"is-{set_slug}-worth-buying-2026"
    title     = f"Is {name} Worth Buying in 2026? Investment Guide"
    desc      = (f"{name} booster box analysis: current price {fmt_gbp(curr_price)}, "
                 f"AI rating {score_row[0] if score_row else 'N/A'}. "
                 f"Full investment breakdown with price history and chase card values.")

    # Verdict logic
    if score_row:
        rec, dscore = score_row[0], score_row[1]
    else:
        rec, dscore = "N/A", None

    if curr_bpct is not None:
        if curr_bpct < 0.7:
            sealed_verdict = f"**Sealed looks undervalued** at a {curr_bpct:.2f}x ratio — singles value exceeds box price."
        elif curr_bpct > 1.3:
            sealed_verdict = f"**Sealed carries a premium** at {curr_bpct:.2f}x singles value — factor in collector demand."
        else:
            sealed_verdict = f"**Sealed and singles are broadly aligned** at {curr_bpct:.2f}x ratio."
    else:
        sealed_verdict = "Price-to-singles ratio not available."

    md = f"""# Is {name} Worth Buying in 2026?

*Last updated: {date.today().strftime("%B %Y")} | Era: {era} | Status: {print_status or "Active"}*

## Quick Verdict

**TCGInvest AI Rating: {rec}** {"(Score: " + str(dscore) + "/25)" if dscore else ""}

{sealed_verdict}

## Current Price

| Metric | Value |
|--------|-------|
| Booster Box (UK) | **{fmt_gbp(curr_price)}** |
| Singles Value (set total) | {fmt_gbp(curr_sv)} |
| Sealed/Singles Ratio | {f"{curr_bpct:.2f}x" if curr_bpct else "N/A"} |
| Set Era | {era} |
| Print Status | {print_status or "In print"} |
"""

    if score_row:
        md += f"""
## AI Investment Scores

| Factor | Score |
|--------|-------|
| Scarcity | {score_row[2]}/5 |
| Liquidity | {score_row[3]}/5 |
| Mascot Power | {score_row[4]}/5 |
| Set Depth | {score_row[5]}/5 |
| **Overall** | **{dscore}/25** |

*Scores generated by Groq llama-3.3-70b using live TCGInvest data.*
"""

    if snapshots:
        md += "\n## Price History\n\n| Month | Box Price | Singles Value | Ratio |\n|-------|-----------|---------------|-------|\n"
        for snap in snapshots:
            md += f"| {month_label(str(snap[0]))} | {fmt_gbp(snap[1])} | {fmt_gbp(snap[2])} | {f'{float(snap[3]):.2f}x' if snap[3] else 'N/A'} |\n"

        if trend_pct is not None:
            direction = "up" if trend_pct > 0 else "down"
            md += f"\n*Price has moved **{direction} {abs(trend_pct):.1f}%** over the last {len(snapshots)} months.*\n"

    if chase_cards:
        md += "\n## Top Chase Cards\n\n| Card | Raw (GBP) | PSA 10 (GBP) |\n|------|-----------|-------------|\n"
        for cc in chase_cards:
            card_name, rarity, raw, psa10 = cc
            md += f"| {card_name} | {fmt_gbp(raw)} | {fmt_gbp(psa10)} |\n"

        top_raw = float(chase_cards[0][2]) if chase_cards[0][2] else 0
        if curr_price and top_raw:
            pulls_needed = round(curr_price / top_raw, 1) if top_raw > 0 else "N/A"
            md += f"\n*Top chase card ({chase_cards[0][0]}) at {fmt_gbp(top_raw)} — you'd need roughly {pulls_needed} boxes worth of value to break even on pull rate alone.*\n"

    md += f"""
## Should You Buy {name}?

"""
    if rec in ("Strong Buy", "Buy"):
        md += f"Based on current data, {name} presents a **{rec.lower()}** opportunity. "
        if print_status and "OOP" in print_status:
            md += "With print runs ending, supply will only decrease. "
        md += f"At {fmt_gbp(curr_price)} per box, the risk/reward profile looks favourable for long-term holders."
    elif rec in ("Accumulate",):
        md += f"{name} is rated **Accumulate** — worth building a position gradually rather than going all-in. "
        md += "Price momentum and fundamentals are positive but not yet at peak entry signal."
    else:
        md += f"Current data rates {name} as **{rec}**. Monitor price trends before committing significant capital."

    md += f"""

*[Track {name} live prices and scores →](/sets/{set_slug})*

---
*Data sourced from TCGInvest's pipeline of eBay UK sold listings and AI scoring. Updated weekly.*
"""

    upsert_blog_post(conn, slug, title, desc, "guide", md, featured=False)


# ── PILLAR 4: Chase Card Deep-Dive ────────────────────────────────────────────

def generate_chase_card_deepdive(conn, card_id=None):
    """
    Pillar 3: Chase card deep-dives — pull rate, PSA premium, grading ROI.
    Slug: chase-card-[card-slug]-investment-guide
    """
    cur = conn.cursor()

    if card_id:
        cur.execute("""
            SELECT cc.id, cc.card_name, cc.rarity, cc.pull_rate_per_box,
                   s.name AS set_name, s.era, s.id AS set_id
            FROM chase_cards cc JOIN sets s ON s.id = cc.set_id
            WHERE cc.id = %s
        """, (card_id,))
    else:
        return

    row = cur.fetchone()
    if not row:
        print(f"  Chase card not found: {card_id}")
        return

    cid, card_name, rarity, pull_rate, set_name, era, set_id = row

    # Price history for this card
    cur.execute("""
        SELECT snapshot_date, raw_gbp, psa10_gbp, price_source
        FROM chase_card_prices
        WHERE chase_card_id = %s
        ORDER BY snapshot_date DESC LIMIT 14
    """, (cid,))
    price_rows = cur.fetchall()

    if not price_rows:
        print(f"  No price data for card {card_name} — skipping")
        return

    latest_price = price_rows[0]
    raw_gbp   = float(latest_price[1]) if latest_price[1] else None
    psa10_gbp = float(latest_price[2]) if latest_price[2] else None

    # PSA grading premium
    psa_premium = None
    if raw_gbp and psa10_gbp and raw_gbp > 0:
        psa_premium = round((psa10_gbp - raw_gbp) / raw_gbp * 100, 1)

    # Set context — current box price for pull rate math
    cur.execute("""
        SELECT bb_price_gbp FROM monthly_snapshots
        WHERE set_id = %s ORDER BY run_date DESC LIMIT 1
    """, (set_id,))
    box_row = cur.fetchone()
    box_price = float(box_row[0]) if box_row and box_row[0] else None

    card_slug = slugify(card_name)
    slug  = f"chase-card-{card_slug}-investment-guide"
    title = f"{card_name} — Price & Investment Guide"
    desc  = (f"{card_name} from {set_name}: raw {fmt_gbp(raw_gbp)}, PSA 10 {fmt_gbp(psa10_gbp)}. "
             f"Pull rates, grading ROI, and investment analysis.")

    md = f"""# {card_name} — Investment & Grading Guide

*From {set_name} ({era}) | Last updated: {date.today().strftime("%B %Y")}*

## Current Prices

| Grade | Price (GBP) |
|-------|-------------|
| Raw (ungraded) | **{fmt_gbp(raw_gbp)}** |
| PSA 10 (gem mint) | **{fmt_gbp(psa10_gbp)}** |
| PSA Premium | {f"+{psa_premium}%" if psa_premium else "N/A"} |
"""

    if rarity:
        md += f"| Rarity | {rarity} |\n"
    if pull_rate:
        md += f"| Pull Rate | ~1 in {pull_rate} boxes |\n"

    if box_price and pull_rate and raw_gbp:
        cost_to_pull = float(box_price) * float(pull_rate)
        roi_pct = round((raw_gbp - cost_to_pull) / cost_to_pull * 100, 1) if cost_to_pull else None
        md += f"""
## Pull Rate Economics

At the current box price of {fmt_gbp(box_price)}:

- **Cost to pull**: ~{fmt_gbp(cost_to_pull)} (buying boxes until you hit this card)
- **Card raw value**: {fmt_gbp(raw_gbp)}
- **Pull ROI**: {"+" if roi_pct and roi_pct > 0 else ""}{fmt_pct(roi_pct) if roi_pct else "N/A"} {"✅" if roi_pct and roi_pct > 0 else "❌" if roi_pct else ""}

*{"Mathematically positive pull rate — rare for modern sets." if roi_pct and roi_pct > 0 else "Negative pull ROI is normal — sealed value comes from all cards in the set, not just this one."}*
"""

    if psa10_gbp and raw_gbp:
        grading_cost = 25  # approx PSA sub fee in GBP
        grading_breakeven = raw_gbp + grading_cost
        grading_profit = psa10_gbp - grading_breakeven if psa10_gbp > grading_breakeven else None
        md += f"""
## Should You Grade This Card?

PSA grading costs approximately £{grading_cost} per card (submission + shipping).

| Scenario | Value |
|----------|-------|
| Send raw card to PSA | Raw: {fmt_gbp(raw_gbp)} + £{grading_cost} fees = {fmt_gbp(grading_breakeven)} break-even |
| PSA 10 result | {fmt_gbp(psa10_gbp)} |
| Profit if PSA 10 | {fmt_gbp(grading_profit) if grading_profit else "Below break-even"} |

*{"Grading looks profitable if you pull this card — the PSA 10 premium justifies the fees." if grading_profit and grading_profit > 0 else "Raw price and grading costs are close — grading is speculative at current prices."}*
"""

    if price_rows:
        md += "\n## Recent Price History\n\n| Date | Raw | PSA 10 |\n|------|-----|--------|\n"
        for pr in price_rows[:7]:
            md += f"| {pr[0]} | {fmt_gbp(pr[1])} | {fmt_gbp(pr[2])} |\n"

    md += f"""
## Investment Summary

**{card_name}** from {set_name} is one of the{"" if not rarity else f" {rarity}"} chase cards in the {era} era.
"""
    if psa_premium and psa_premium > 200:
        md += f"The {psa_premium}% PSA 10 premium reflects strong collector demand for top-grade copies. "
    if pull_rate and float(pull_rate) > 10:
        md += f"With a pull rate of ~1 in {pull_rate} boxes, raw copies are scarce from pack opening. "

    md += f"""
*[Track {set_name} booster box prices →](/sets/{slugify(set_name)})*
*[Browse all chase cards →](/tools/chase-cards)*

---
*Data from TCGInvest daily price scrape (PriceCharting). Updated daily.*
"""

    upsert_blog_post(conn, slug, title, desc, "analysis", md, featured=False)


# ── PILLAR 5: Sealed vs Singles ───────────────────────────────────────────────

def generate_sealed_vs_singles(conn, set_id=None, set_name=None):
    """
    Pillar 4: "Should you buy sealed or singles for [Set]?"
    Slug: sealed-vs-singles-[set-slug]
    """
    cur = conn.cursor()

    if set_id:
        cur.execute("SELECT id, name, era, print_status FROM sets WHERE id = %s", (set_id,))
    elif set_name:
        cur.execute("SELECT id, name, era, print_status FROM sets WHERE name ILIKE %s", (set_name,))
    else:
        return

    row = cur.fetchone()
    if not row:
        print(f"  Set not found for sealed_vs_singles")
        return

    sid, name, era, print_status = row

    cur.execute("""
        SELECT bb_price_gbp, set_value_gbp, box_pct, run_date
        FROM monthly_snapshots WHERE set_id = %s ORDER BY run_date DESC LIMIT 1
    """, (sid,))
    snap = cur.fetchone()
    if not snap or not snap[0]:
        print(f"  No snapshot for {name} — skipping sealed_vs_singles")
        return

    bb_price, sv_gbp, box_pct, run_date = snap
    bb_price = float(bb_price)
    sv_gbp   = float(sv_gbp) if sv_gbp else None
    box_pct  = float(box_pct) if box_pct else None

    # Top chase cards
    cur.execute("""
        SELECT cc.card_name, ccp.raw_gbp, ccp.psa10_gbp
        FROM chase_cards cc
        LEFT JOIN chase_card_prices ccp ON ccp.chase_card_id = cc.id
        WHERE cc.set_id = %s
        ORDER BY ccp.raw_gbp DESC NULLS LAST
    """, (sid,))
    chase_raw = cur.fetchall()
    seen = {}
    for r in chase_raw:
        if r[0] not in seen:
            seen[r[0]] = r
    top_chase = list(seen.values())[:4]

    set_slug = slugify(name)
    slug  = f"sealed-vs-singles-{set_slug}"
    title = f"Sealed vs Singles: {name} — Which Should You Buy?"
    desc  = (f"Should you buy {name} booster boxes or individual cards? "
             f"Data-driven breakdown with current prices and investment verdict.")

    # Verdict
    if box_pct is not None:
        if box_pct < 0.7:
            verdict = "**Singles dominate.** Box price is significantly below singles total value — sealed is relatively cheap."
            verdict_reason = ("This means buying a box gives you exposure to the full singles value at a discount. "
                             "However, you'd need to sell every card to realise that value — transaction costs and time apply.")
            rec = "Sealed"
        elif box_pct > 1.3:
            verdict = "**Singles are better value.** The booster box trades at a premium to the singles total."
            verdict_reason = ("Collectors are paying a scarcity or nostalgia premium for sealed product. "
                             "Buying the specific singles you want is more capital-efficient.")
            rec = "Singles"
        else:
            verdict = "**It's roughly equal.** Sealed and singles are within the same value band."
            verdict_reason = "Your choice should depend on your goal: speculation (sealed) vs specific card access (singles)."
            rec = "Either"
    else:
        verdict = "Insufficient data for a direct comparison."
        verdict_reason = ""
        rec = "N/A"

    md = f"""# Sealed vs Singles: {name}

*Data from {month_label(str(run_date))} | Era: {era} | Status: {print_status or "Active"}*

## The Quick Answer

{verdict}

{verdict_reason}

## Price Comparison

| Metric | Value |
|--------|-------|
| Booster Box Price | **{fmt_gbp(bb_price)}** |
| Full Singles Value | {fmt_gbp(sv_gbp)} |
| Sealed/Singles Ratio | {f"{box_pct:.2f}x" if box_pct else "N/A"} |

*A ratio below 1.0 means sealed is cheaper than buying all singles individually.*
*A ratio above 1.0 means sealed commands a premium.*

## Why Buy Sealed ({name})?

- **Speculation play:** Sealed boxes appreciate when sets go out of print (OOP)
- **Convenience:** One purchase, full set exposure
- **Grading potential:** Sealed preservation can generate PSA 10 hits
{"- **Supply risk:** " + print_status + " — supply declining" if print_status and "OOP" in print_status else ""}

## Why Buy Singles ({name})?

- **Capital efficiency:** Target only the cards you want
- **No RNG:** Pay market rate, no pull rate variance
- **Lower barrier:** Start with £10 vs {fmt_gbp(bb_price)} for a box
- **Liquidity:** Individual cards trade more frequently than sealed boxes
"""

    if top_chase:
        md += f"\n## Key Singles to Consider\n\n| Card | Raw Price | PSA 10 |\n|------|-----------|--------|\n"
        for cc in top_chase:
            md += f"| {cc[0]} | {fmt_gbp(cc[1])} | {fmt_gbp(cc[2])} |\n"

    md += f"""
## Our Verdict

**Recommended approach: {rec}**

For {name} specifically, the data{"" if rec == "N/A" else f" points toward **{rec.lower()}**"}. 
{"The sealed product is priced attractively relative to singles, making boxes a reasonable way to gain diversified exposure." if rec == "Sealed" else "Buying individual singles targets your capital more precisely at current valuations." if rec == "Singles" else "Both approaches have merit depending on your investment thesis."}

*[View {name} price history →](/sets/{set_slug})*
*[Full Booster Box Tracker →](/tools/tracker)*

---
*Prices from TCGInvest monthly pipeline (eBay UK sold listings). Updated weekly.*
"""

    upsert_blog_post(conn, slug, title, desc, "analysis", md, featured=False)


# ── PILLAR 6: Era / Rotation Guide ───────────────────────────────────────────

def generate_era_rotation_guide(conn, era):
    """
    Pillar 5: "Best [Era] sets to invest in 2026"
    Slug: best-[era-slug]-sets-to-invest-2026
    """
    cur = conn.cursor()

    cur.execute("""
        SELECT
            s.id, s.name, s.print_status, s.date_released,
            ms.bb_price_gbp, ms.set_value_gbp, ms.box_pct,
            sc.recommendation, sc.decision_score
        FROM sets s
        JOIN monthly_snapshots ms ON ms.set_id = s.id
        LEFT JOIN scores sc ON sc.set_id = s.id AND sc.run_date = ms.run_date
        WHERE s.era = %s
          AND ms.run_date = (SELECT MAX(run_date) FROM monthly_snapshots WHERE set_id = s.id)
        ORDER BY sc.decision_score DESC NULLS LAST, ms.bb_price_gbp DESC NULLS LAST
    """, (era,))
    era_sets = cur.fetchall()

    if not era_sets:
        print(f"  No data for era: {era} — skipping")
        return

    era_slug = slugify(era)
    slug  = f"best-{era_slug}-sets-to-invest-2026"
    title = f"Best {era} Pokémon TCG Sets to Invest in 2026"
    desc  = (f"Ranked guide to {era} era Pokémon TCG booster boxes by investment potential. "
             f"Covers {len(era_sets)} sets with AI scores, price history, and investment verdicts.")

    # Top pick
    top = era_sets[0]
    top_name = top[1]
    top_price = fmt_gbp(top[4])
    top_rec   = top[7] or "N/A"

    # OOP vs in-print split
    oop_sets    = [s for s in era_sets if s[2] and "OOP" in s[2]]
    active_sets = [s for s in era_sets if not s[2] or "OOP" not in s[2]]

    md = f"""# Best {era} Pokémon TCG Sets to Invest in 2026

*Ranked by AI investment score | Data: {date.today().strftime("%B %Y")} | {len(era_sets)} sets tracked*

## Top Pick: {top_name}

At {top_price}, **{top_name}** leads the {era} era with an AI rating of **{top_rec}**. 
{"This set is out of print, making sealed supply finite." if top[2] and "OOP" in top[2] else "Still in print, offering accessible entry points."}

## Full {era} Rankings

| Rank | Set | Box Price | Singles Value | Ratio | AI Score | Rating |
|------|-----|-----------|---------------|-------|----------|--------|
"""
    for i, s in enumerate(era_sets, 1):
        sid, sname, pstatus, dreleased, bb, sv, bpct, rec, dscore = s
        md += (f"| {i} | [{sname}](/sets/{slugify(sname)}) | {fmt_gbp(bb)} | {fmt_gbp(sv)} | "
               f"{f'{float(bpct):.2f}x' if bpct else 'N/A'} | {dscore or 'N/A'}/25 | {rec or 'N/A'} |\n")

    if oop_sets:
        md += f"""
## Out of Print {era} Sets

These {era} sets are confirmed out of print — supply is finite and declining:

"""
        for s in oop_sets:
            md += f"- **[{s[1]}](/sets/{slugify(s[1])})** — {fmt_gbp(s[4])} | {s[2]} | AI: {s[7] or 'N/A'}\n"
        md += "\n*OOP sets historically appreciate 2–5 years post-discontinuation as supply diminishes.*\n"

    if active_sets:
        md += f"""
## Still in Print

These {era} sets remain in active production — lower scarcity premium but more accessible pricing:

"""
        for s in active_sets[:5]:
            md += f"- **[{s[1]}](/sets/{slugify(s[1])})** — {fmt_gbp(s[4])} | AI: {s[7] or 'N/A'}\n"

    # Value ratio analysis
    undervalued = [s for s in era_sets if s[6] and float(s[6]) < 0.8]
    if undervalued:
        md += f"\n## Undervalued {era} Sets (Sealed < 80% of Singles Value)\n\n"
        for s in undervalued:
            md += f"- **[{s[1]}](/sets/{slugify(s[1])})** — {float(s[6]):.2f}x ratio at {fmt_gbp(s[4])}\n"

    md += f"""
## {era} Era Investment Strategy

The {era} era {"has fully concluded with no new sets expected" if era in ("SM", "SWSH") else "is actively producing new sets"}. 
{"This makes sealed product an increasingly scarce asset." if era in ("SM", "SWSH") else "New releases create buying opportunities in older sets as collector attention shifts."}

Key {era} investment considerations:
- **Demand drivers:** Popular Pokémon, iconic artwork, and nostalgia
- **Supply:** {"Finite — OOP sets only available on secondary market" if era in ("SM", "SWSH") else "Mixed — some OOP, some active print"}
- **Liquidity:** {era} boxes trade regularly on eBay UK
- **Time horizon:** 3–5 years recommended for sealed product appreciation

*[Track all {era} sets on the Booster Box Tracker →](/tools/tracker)*

---
*Rankings based on TCGInvest AI scores (Groq llama-3.3-70b) and monthly price pipeline data.*
"""

    upsert_blog_post(conn, slug, title, desc, "guide", md, featured=False)


# ── Weekly runner ─────────────────────────────────────────────────────────────

def run_weekly(conn, regen_all=False):
    """
    Standard weekly run:
    - Always: movers post + price trend report
    - First-time (or regen_all): set guides, era guides for all sets/eras
    - Chase deepdives: only for cards with price data
    """
    print("\n=== PILLAR 1 & 2: Movers + Price Trend ===")
    generate_movers_post(conn)
    generate_price_trend_report(conn)

    cur = conn.cursor()

    # Era guides — one per era
    print("\n=== PILLAR 5: Era Guides ===")
    cur.execute("SELECT DISTINCT era FROM sets ORDER BY era")
    eras = [r[0] for r in cur.fetchall()]
    for era in eras:
        # Only regen if missing or regen_all
        era_slug = slugify(era)
        slug = f"best-{era_slug}-sets-to-invest-2026"
        cur.execute("SELECT id FROM blog_posts WHERE slug = %s", (slug,))
        exists = cur.fetchone()
        if not exists or regen_all:
            print(f"  Generating era guide: {era}")
            generate_era_rotation_guide(conn, era)
        else:
            print(f"  Era guide exists (skip): {era}")

    # Set guides — one per set with price data
    print("\n=== PILLAR 1: Set Investment Guides ===")
    cur.execute("""
        SELECT DISTINCT s.id FROM sets s
        JOIN monthly_snapshots ms ON ms.set_id = s.id
        WHERE ms.bb_price_gbp IS NOT NULL
    """)
    set_ids = [r[0] for r in cur.fetchall()]
    for sid in set_ids:
        cur.execute("SELECT name FROM sets WHERE id = %s", (sid,))
        sname = cur.fetchone()[0]
        slug = f"is-{slugify(sname)}-worth-buying-2026"
        cur.execute("SELECT id FROM blog_posts WHERE slug = %s", (slug,))
        exists = cur.fetchone()
        if not exists or regen_all:
            print(f"  Generating set guide: {sname}")
            generate_set_investment_guide(conn, set_id=sid)
        else:
            print(f"  Set guide exists (skip): {sname}")

    # Sealed vs singles — same set list
    print("\n=== PILLAR 4: Sealed vs Singles ===")
    for sid in set_ids:
        cur.execute("SELECT name FROM sets WHERE id = %s", (sid,))
        sname = cur.fetchone()[0]
        slug = f"sealed-vs-singles-{slugify(sname)}"
        cur.execute("SELECT id FROM blog_posts WHERE slug = %s", (slug,))
        exists = cur.fetchone()
        if not exists or regen_all:
            print(f"  Generating sealed vs singles: {sname}")
            generate_sealed_vs_singles(conn, set_id=sid)
        else:
            print(f"  Sealed vs singles exists (skip): {sname}")

    # Chase deepdives — cards with recent price data only
    print("\n=== PILLAR 3: Chase Card Deep-Dives ===")
    cur.execute("""
        SELECT cc.id, cc.card_name, MAX(ccp.raw_gbp) AS max_raw
        FROM chase_cards cc
        JOIN chase_card_prices ccp ON ccp.chase_card_id = cc.id
        WHERE ccp.raw_gbp IS NOT NULL
        GROUP BY cc.id, cc.card_name
        ORDER BY max_raw DESC NULLS LAST
        LIMIT 20
    """)
    card_rows = cur.fetchall()
    for card_id, card_name, _raw in card_rows:
        slug = f"chase-card-{slugify(card_name)}-investment-guide"
        cur.execute("SELECT id FROM blog_posts WHERE slug = %s", (slug,))
        exists = cur.fetchone()
        if not exists or regen_all:
            print(f"  Generating chase deepdive: {card_name}")
            generate_chase_card_deepdive(conn, card_id=card_id)
        else:
            print(f"  Chase deepdive exists (skip): {card_name}")

    print("\n✓ Weekly run complete")


def rebuild_frontend():
    print("\n=== Building frontend ===")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("BUILD FAILED:")
        print(result.stdout[-2000:])
        print(result.stderr[-1000:])
        sys.exit(1)
    print("Build succeeded")
    subprocess.run(["pm2", "restart", "tcginvest-frontend"], check=True)
    print("PM2 restarted")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TCGInvest Blog Post Generator v3")
    parser.add_argument("--pillar", choices=["movers","price_trend","set_guide","chase_deepdive","sealed_vs_singles","era_guide"],
                        help="Run a single pillar only")
    parser.add_argument("--set-id",  type=int, help="Set ID for set_guide / sealed_vs_singles")
    parser.add_argument("--card-id", type=int, help="Chase card ID for chase_deepdive")
    parser.add_argument("--era",     type=str, help="Era string for era_guide (e.g. SWSH)")
    parser.add_argument("--all-sets",  action="store_true", help="Regenerate all set guides")
    parser.add_argument("--all-cards", action="store_true", help="Regenerate all chase deepdives")
    parser.add_argument("--all-eras",  action="store_true", help="Regenerate all era guides")
    parser.add_argument("--no-rebuild", action="store_true", help="Skip frontend rebuild")
    args = parser.parse_args()

    print(f"=== Blog Post Generator v3 — {date.today()} ===")

    conn = get_db_conn()

    if args.pillar:
        if args.pillar == "movers":
            generate_movers_post(conn)
        elif args.pillar == "price_trend":
            generate_price_trend_report(conn)
        elif args.pillar == "set_guide":
            if args.all_sets:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT set_id FROM monthly_snapshots WHERE bb_price_gbp IS NOT NULL")
                for (sid,) in cur.fetchall():
                    generate_set_investment_guide(conn, set_id=sid)
            elif args.set_id:
                generate_set_investment_guide(conn, set_id=args.set_id)
            else:
                print("--set-id required for set_guide pillar (or use --all-sets)")
                sys.exit(1)
        elif args.pillar == "chase_deepdive":
            if args.all_cards:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT chase_card_id FROM chase_card_prices WHERE raw_gbp IS NOT NULL")
                for (cid,) in cur.fetchall():
                    generate_chase_card_deepdive(conn, card_id=cid)
            elif args.card_id:
                generate_chase_card_deepdive(conn, card_id=args.card_id)
            else:
                print("--card-id required for chase_deepdive (or use --all-cards)")
                sys.exit(1)
        elif args.pillar == "sealed_vs_singles":
            if args.all_sets:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT set_id FROM monthly_snapshots WHERE bb_price_gbp IS NOT NULL")
                for (sid,) in cur.fetchall():
                    generate_sealed_vs_singles(conn, set_id=sid)
            elif args.set_id:
                generate_sealed_vs_singles(conn, set_id=args.set_id)
            else:
                print("--set-id required (or use --all-sets)")
                sys.exit(1)
        elif args.pillar == "era_guide":
            if args.all_eras:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT era FROM sets")
                for (era,) in cur.fetchall():
                    generate_era_rotation_guide(conn, era)
            elif args.era:
                generate_era_rotation_guide(conn, args.era)
            else:
                print("--era required for era_guide (or use --all-eras)")
                sys.exit(1)
    else:
        # Full weekly run
        regen = args.all_sets or args.all_cards or args.all_eras
        run_weekly(conn, regen_all=regen)

    conn.close()

    if not args.no_rebuild:
        rebuild_frontend()
    else:
        print("(--no-rebuild: skipping build)")
