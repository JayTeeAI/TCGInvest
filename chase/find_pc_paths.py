#!/usr/bin/env python3
"""
For each chase card without a pc_path, search PriceCharting to find the correct URL.
Uses card name + set name to search, picks the best match.
"""
import os, re, time
from dotenv import load_dotenv
load_dotenv('/root/.openclaw/api/.env')
import psycopg2, psycopg2.extras
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

PC_BASE = 'https://www.pricecharting.com'
SLEEP   = 1.0

pg  = psycopg2.connect(os.getenv('DATABASE_URL'))
pg.cursor_factory = psycopg2.extras.RealDictCursor
cur = pg.cursor()

cur.execute('''
    SELECT cc.id, cc.card_name, s.name AS set_name
    FROM chase_cards cc
    JOIN sets s ON s.id = cc.set_id
    WHERE cc.pc_path IS NULL AND cc.active = TRUE
    ORDER BY s.name, cc.card_name
''')
cards = cur.fetchall()
print(f'Finding PC paths for {len(cards)} cards...\n')

found = not_found = 0

for card in cards:
    # Build search query from card name, stripping rarity suffixes
    base_name = re.sub(r'\s*\(.*\)$', '', card['card_name']).strip()
    query = f"{base_name} {card['set_name']}".replace(' ', '+')
    url   = f"{PC_BASE}/search-products?q={query}&type=prices"

    try:
        r    = cffi_requests.get(url, impersonate='chrome110', timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select('table#games_table tbody tr')

        best_path = None
        best_score = -1

        name_lower = base_name.lower()
        set_lower  = card['set_name'].lower().replace(' ', '-')

        for row in rows[:8]:
            a = row.find('a', href=lambda h: h and '/game/pokemon-' in h and 'japanese' not in h.lower())
            if not a: continue
            href = a['href'].replace(PC_BASE, '')
            href_lower = href.lower()

            # Score match quality
            score = 0
            for word in name_lower.split():
                if word in href_lower: score += 1
            # Bonus if set name words appear in path
            for word in set_lower.split('-'):
                if len(word) > 3 and word in href_lower: score += 1

            if score > best_score:
                best_score = score
                best_path  = href

        if best_path and best_score >= 2:
            cur.execute('UPDATE chase_cards SET pc_path=%s WHERE id=%s', (best_path, card['id']))
            pg.commit()
            print(f'  OK  [{card["set_name"]}] {card["card_name"]:40s} -> {best_path}')
            found += 1
        else:
            print(f'  --- [{card["set_name"]}] {card["card_name"]:40s}  (no match, score={best_score})')
            not_found += 1

    except Exception as e:
        print(f'  ERR [{card["set_name"]}] {card["card_name"]}: {e}')
        not_found += 1

    time.sleep(SLEEP)

print(f'\nDone. Found: {found} | Not found: {not_found}')
cur.close(); pg.close()
