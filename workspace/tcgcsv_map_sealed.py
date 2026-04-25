#!/usr/bin/env python3
"""
tcgcsv_map_sealed.py — Map TCGCSV product IDs for booster boxes and PC ETBs
Fetches the products endpoint for each set's group_ids, identifies:
  - Booster Box (single box, not case/half/display)
  - Pokemon Center ETB (PC exclusive ETB, single unit)
Updates sets.tcgcsv_bb_product_id, sets.tcgcsv_etb_product_id
Also maps etbs.tcgcsv_product_id by matching ETB name to PC ETB product names.

Run once (or re-run to refresh mappings).
"""

import time
import requests
import psycopg2
import psycopg2.extras
import re

DATABASE_URL = "host=localhost dbname=tcginvest user=tcginvest password=pxQSY8IjfYEsiBSd42e6ke+h4tmO1eFU705sLqYHJEU="
CATEGORY_ID  = 3
BASE_URL     = "https://tcgcsv.com/tcgplayer"
HEADERS      = {
    "User-Agent": "TCGInvest/1.0 (tcginvest.uk; +https://tcginvest.uk)",
    "Accept": "application/json",
}

EXCLUDE_BB   = re.compile(r'case|half|display|bundle|blister|pack|tin|box set', re.I)
EXCLUDE_ETB  = re.compile(r'case|set of|bundle', re.I)


def fetch_products(group_id):
    url = f"{BASE_URL}/{CATEGORY_ID}/{group_id}/products"
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json().get("results", [])


def pick_bb(products):
    """Return the single booster box product ID, or None."""
    candidates = []
    for p in products:
        name = p.get("name", "")
        if "booster box" in name.lower() and not EXCLUDE_BB.search(name):
            candidates.append((p["productId"], name))
    if not candidates:
        return None
    # Prefer shortest name (most generic, avoids bundles)
    candidates.sort(key=lambda x: len(x[1]))
    return candidates[0][0]


def pick_pc_etb(products):
    """Return the single PC ETB product ID (single unit), or None."""
    candidates = []
    for p in products:
        name = p.get("name", "")
        nl = name.lower()
        if "pokemon center elite trainer box" in nl and not EXCLUDE_ETB.search(name):
            candidates.append((p["productId"], name))
    if not candidates:
        return None
    candidates.sort(key=lambda x: len(x[1]))
    return candidates[0][0]


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT id, name, tcgcsv_group_ids FROM sets WHERE tcgcsv_group_ids IS NOT NULL AND tcgcsv_group_ids != '{}'")
    sets = cur.fetchall()
    print(f"Mapping {len(sets)} sets...")

    for s in sets:
        set_id   = s["id"]
        set_name = s["name"]
        group_ids = s["tcgcsv_group_ids"] or []

        bb_pid  = None
        etb_pid = None
        all_products = []

        for gid in group_ids:
            products = fetch_products(gid)
            all_products.extend(products)
            time.sleep(0.15)

        if not all_products:
            print(f"  [{set_id}] {set_name}: no products found")
            continue

        bb_pid  = pick_bb(all_products)
        etb_pid = pick_pc_etb(all_products)

        cur2 = conn.cursor()
        cur2.execute(
            "UPDATE sets SET tcgcsv_bb_product_id=%s, tcgcsv_etb_product_id=%s WHERE id=%s",
            (bb_pid, etb_pid, set_id)
        )
        conn.commit()
        print(f"  [{set_id}] {set_name}: BB={bb_pid}, PC-ETB={etb_pid}")

    # Now map etbs.tcgcsv_product_id
    # For each ETB, find its set's group_ids, fetch products, match PC ETB by name similarity
    cur.execute("""
        SELECT e.id, e.name, e.set_id, s.tcgcsv_group_ids, s.tcgcsv_etb_product_id
        FROM etbs e
        JOIN sets s ON e.set_id = s.id
    """)
    etb_rows = cur.fetchall()
    print(f"\nMapping {len(etb_rows)} ETBs...")

    for e in etb_rows:
        # If only 1 PC ETB product on the set, use that
        pid = e["tcgcsv_etb_product_id"]
        if pid:
            cur2 = conn.cursor()
            cur2.execute("UPDATE etbs SET tcgcsv_product_id=%s WHERE id=%s", (pid, e["id"]))
            conn.commit()
            print(f"  [etb {e['id']}] {e['name']}: product_id={pid}")
        else:
            print(f"  [etb {e['id']}] {e['name']}: no PC ETB found for set {e['set_id']}")

    print("\nDone.")
    conn.close()


if __name__ == "__main__":
    main()
