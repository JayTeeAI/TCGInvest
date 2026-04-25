#!/usr/bin/env python3
"""
TCGInvest Blog Post Auto-Generator
Runs monthly (BB movers) and weekly (ETB movers once data available).
Generates file-based blog posts and triggers a frontend rebuild.
"""

import os
import sys
import json
import re
import urllib.request
import subprocess
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/root/.openclaw/api/.env")
API_KEY = os.getenv("API_KEY", "")
API_BASE = "http://127.0.0.1:8000"
POSTS_LIB = "/root/.openclaw/frontend/lib/blog/posts.ts"
COMPONENTS_DIR = "/root/.openclaw/frontend/components/blog"
FRONTEND_DIR = "/root/.openclaw/frontend"

def api_get(path):
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"X-API-Key": API_KEY}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def slugify(name):
    s = name.lower().replace("s&v", "sandv").replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def get_movers():
    try:
        data = api_get("/api/movers")
    except Exception as e:
        print(f"API error: {e}")
        return None, None, None, None

    movers = data.get("movers", [])
    latest = data.get("latest")
    previous = data.get("previous")

    if not movers or not latest or not previous:
        print("Not enough data for movers post")
        return None, None, None, None

    # Normalise keys from API response
    normalised = []
    for m in movers:
        normalised.append({
            "name": m.get("name"),
            "era": m.get("era"),
            "curr_price": m.get("curr_bb"),
            "prev_price": m.get("prev_bb"),
            "pct_change": m.get("bb_change_pct"),
            "rec": m.get("curr_rec"),
            "score": m.get("curr_score"),
        })

    gainers = sorted([m for m in normalised if m["pct_change"] and m["pct_change"] > 0], key=lambda x: -x["pct_change"])[:5]
    drops = sorted([m for m in normalised if m["pct_change"] and m["pct_change"] < 0], key=lambda x: x["pct_change"])[:5]
    return gainers, drops, latest, previous

def month_label(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%B %Y")

def generate_movers_component(gainers, drops, latest, previous):
    today = date.today()
    month_str = today.strftime("%B %Y").lower().replace(" ", "-")
    slug = f"pokemon-booster-box-movers-{month_str}"
    title = f"Pokemon TCG Booster Box Price Movers — {today.strftime('%B %Y')}"
    description = f"{gainers[0]['name']} up {gainers[0]['pct_change']}%, {drops[0]['name']} drops {abs(drops[0]['pct_change'])}%. This month's biggest sealed product price movements across 43 tracked sets."

    def gain_row(m):
        slug_ = slugify(m["name"])
        return f'''          <GainRow name="{m['name']}" slug="{slug_}" prev={{{m['prev_price']}}} curr={{{m['curr_price']}}} pct={{{m['pct_change']}}} rec="{m['rec'] or 'N/A'}" />'''

    def drop_row(m):
        slug_ = slugify(m["name"])
        return f'''          <DropRow name="{m['name']}" slug="{slug_}" prev={{{m['prev_price']}}} curr={{{m['curr_price']}}} pct={{{m['pct_change']}}} rec="{m['rec'] or 'N/A'}" />'''

    gainer_rows = "\n".join(gain_row(m) for m in gainers)
    drop_rows = "\n".join(drop_row(m) for m in drops)
    comp_name = f"MoverPost{today.strftime('%b%Y')}Content"
    comp_file = f"{COMPONENTS_DIR}/MoverPost{today.strftime('%b%Y')}Content.tsx"

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
          {month_label(latest)} vs {month_label(previous)} comparison across 43 tracked booster box sets.
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
        Next update: following monthly pipeline run.
      </p>
    </div>
  )
}}
'''

    with open(comp_file, "w") as f:
        f.write(component)
    print(f"Written component: {comp_file}")
    return slug, title, description, comp_name, today.strftime("%Y-%m-%d"), comp_file

def update_posts_registry(slug, title, description, post_date):
    with open(POSTS_LIB, "r") as f:
        src = f.read()

    # Check if slug already exists
    if slug in src:
        print(f"Post {slug} already in registry — skipping")
        return False

    new_entry = f'''  {{
    slug: "{slug}",
    title: "{title}",
    description: "{description}",
    date: "{post_date}",
    category: "movers",
    readTime: 4,
    featured: true,
  }},'''

    # Insert at start of posts array
    src = src.replace("export const posts: BlogPost[] = [", f"export const posts: BlogPost[] = [\n{new_entry}")
    with open(POSTS_LIB, "w") as f:
        f.write(src)
    print(f"Added to registry: {slug}")
    return True

def update_blog_post_router(slug, comp_name):
    """Add the new post to the [slug]/page.tsx router"""
    router_path = f"{FRONTEND_DIR}/app/blog/[slug]/page.tsx"
    with open(router_path, "r") as f:
        src = f.read()

    # Add import
    import_line = f'import {{ {comp_name} }} from "@/components/blog/{comp_name}"'
    if comp_name not in src:
        src = src.replace(
            'import { MoverPostContent }',
            f'{import_line}\nimport {{ MoverPostContent }}'
        )
        # Add route
        src = src.replace(
            '{slug === "pokemon-booster-box-movers-april-2026"',
            f'{{slug === "{slug}" && <{comp_name} />}}\n        {{slug === "pokemon-booster-box-movers-april-2026"'
        )
        with open(router_path, "w") as f:
            f.write(src)
        print(f"Router updated for: {slug}")

def update_sitemap(slug):
    sitemap_path = f"{FRONTEND_DIR}/app/sitemap.ts"
    with open(sitemap_path, "r") as f:
        src = f.read()

    if slug in src:
        print(f"Sitemap already has {slug}")
        return

    new_entry = f'''    {{
      url: `${{baseUrl}}/blog/{slug}`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.85,
    }},'''

    marker = '    {\n      url: `${baseUrl}/blog/pokemon-booster-box-movers-april-2026`,'
    if marker in src:
        src = src.replace(marker, new_entry + "\n" + marker)
    with open(sitemap_path, "w") as f:
        f.write(src)
    print(f"Sitemap updated for: {slug}")

def rebuild():
    print("Building...")
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

    print("Restarting PM2...")
    subprocess.run(["pm2", "restart", "tcginvest-frontend"], check=True)
    print("Done")

if __name__ == "__main__":
    print(f"=== Blog Post Generator — {date.today()} ===")
    gainers, drops, latest, previous = get_movers()
    if not gainers:
        sys.exit(0)

    slug, title, description, comp_name, post_date, comp_file = generate_movers_component(
        gainers, drops, latest, previous
    )

    added = update_posts_registry(slug, title, description, post_date)
    if added:
        update_blog_post_router(slug, comp_name)
        update_sitemap(slug)
        rebuild()
    else:
        print("No new post needed — already up to date")
