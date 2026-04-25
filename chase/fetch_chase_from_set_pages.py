#!/usr/bin/env python3
"""
Auto-discover top 3 chase cards per set by scraping PriceCharting set pages.
Sorted by Ungraded price DESC (already the default on PC set pages).
Upserts into chase_cards + chase_card_prices in one pass.
Run weekly via cron.
"""
import os, re, time
from datetime import date
from dotenv import load_dotenv
load_dotenv('/root/.openclaw/api/.env')

import psycopg2, psycopg2.extras
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

PG_CONN  = os.getenv('DATABASE_URL')
PC_BASE  = 'https://www.pricecharting.com'
FX_URL   = 'https://open.er-api.com/v6/latest/USD'
TOP_N    = 5   # candidates to fetch — top 3 shown in UI but extra for fallback
SLEEP    = 1.5

# Mapping: our set_id -> PriceCharting console slug
SET_MAP = {
    7:  'pokemon-hidden-fates',
    13: 'pokemon-shining-fates',
    14: 'pokemon-chilling-reign',
    15: 'pokemon-evolving-skies',
    17: 'pokemon-fusion-strike',
    18: 'pokemon-brilliant-stars',
    19: 'pokemon-astral-radiance',
    20: 'pokemon-lost-origin',
    21: 'pokemon-silver-tempest',
    22: 'pokemon-crown-zenith',
    23: 'pokemon-scarlet-%26-violet',
    24: 'pokemon-paldea-evolved',
    25: 'pokemon-obsidian-flames',
    26: 'pokemon-scarlet-&-violet-151',
    27: 'pokemon-paradox-rift',
    28: 'pokemon-paldean-fates',
    29: 'pokemon-temporal-forces',
    30: 'pokemon-twilight-masquerade',
    31: 'pokemon-shrouded-fable',
    32: 'pokemon-stellar-crown',
    33: 'pokemon-surging-sparks',
    34: 'pokemon-prismatic-evolutions',
    35: 'pokemon-journey-together',
    36: 'pokemon-destined-rivals',
    56: 'pokemon-battle-styles',
}

def get_fx_rate():
    try:
        import requests
        r    = requests.get(FX_URL, timeout=10)
        rate = r.json()['rates']['GBP']
        print(f'FX: 1 USD = {rate:.4f} GBP')
        return rate
    except Exception as e:
        print(f'FX failed: {e} — fallback 0.79')
        return 0.79

def parse_usd(text):
    if not text: return None
    cleaned = re.sub(r'[^\d.]', '', text.replace(',', ''))
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except: return None

def scrape_set_page(console_slug):
    """Returns list of dicts: {name, card_number, pc_path, raw_usd, psa10_usd}"""
    url  = f'{PC_BASE}/console/{console_slug}'
    try:
        r    = cffi_requests.get(url, impersonate='chrome110', timeout=30)
        if r.status_code != 200:
            print(f'  HTTP {r.status_code} for {url}')
            return []
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table', id='games_table')
        if not table:
            print(f'  No games_table found')
            return []

        cards = []
        for row in table.find_all('tr')[1:]:  # skip header
            a = row.find('a', href=True)
            cols = row.find_all('td')
            if not a or len(cols) < 3:
                continue
            href = a['href']
            path = href.replace(PC_BASE, '') if href.startswith('http') else href
            name_text = a.get_text(strip=True)

            # Extract card number from name e.g. "Charizard ex #234"
            num_match = re.search(r'#([A-Z0-9/]+)', name_text)
            card_number = num_match.group(1) if num_match else None
            card_name   = re.sub(r'\s*#.*$', '', name_text).strip()

            # If name is blank (image-only link), derive from URL slug
            if not card_name:
                slug = path.split('/')[-1]
                slug = re.sub(r'-\d+[a-z]?$', '', slug)
                slug = re.sub(r'-%26-', ' & ', slug).replace('-', ' ')
                card_name = re.sub(r'\s+\d+$', '', slug.title()).strip()

            raw_usd   = parse_usd(cols[2].get_text(strip=True)) if len(cols) > 2 else None
            psa10_usd = parse_usd(cols[4].get_text(strip=True)) if len(cols) > 4 else None

            if raw_usd and raw_usd > 0:
                cards.append({
                    'name':        card_name,
                    'card_number': card_number,
                    'pc_path':     path,
                    'raw_usd':     raw_usd,
                    'psa10_usd':   psa10_usd,
                })

        # Already sorted by raw price desc on PC — return top N
        return cards[:TOP_N]

    except Exception as e:
        print(f'  Scrape failed for {console_slug}: {e}')
        return []

def run():
    pg  = psycopg2.connect(PG_CONN)
    pg.cursor_factory = psycopg2.extras.RealDictCursor
    cur = pg.cursor()

    today = date.today().isoformat()
    rate  = get_fx_rate()

    print(f'\nProcessing {len(SET_MAP)} sets...\n')

    for set_id, slug in SET_MAP.items():
        # Get set name for logging
        cur.execute('SELECT name FROM sets WHERE id = %s', (set_id,))
        row = cur.fetchone()
        set_name = row['name'] if row else f'set_{set_id}'
        print(f'[{set_name}] -> /console/{slug}')

        cards = scrape_set_page(slug)
        if not cards:
            print(f'  No cards found — skipping')
            time.sleep(SLEEP)
            continue

        print(f'  Found {len(cards)} top cards:')

        for card in cards:
            raw_gbp   = round(card['raw_usd']   * rate, 2) if card['raw_usd']   else None
            psa10_gbp = round(card['psa10_usd'] * rate, 2) if card['psa10_usd'] else None
            print(f'    {card["name"]:35s} raw=£{raw_gbp}  psa10=£{psa10_gbp}  {card["pc_path"]}')

            # Upsert into chase_cards (keyed on pc_path)
            cur.execute("""
                INSERT INTO chase_cards (set_id, card_name, card_number, pc_path, active)
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT (pc_path) DO UPDATE SET
                    card_name   = EXCLUDED.card_name,
                    card_number = EXCLUDED.card_number,
                    set_id      = EXCLUDED.set_id,
                    active      = TRUE
                RETURNING id
            """, (set_id, card['name'], card['card_number'], card['pc_path']))
            result = cur.fetchone()
            if not result:
                cur.execute("SELECT id FROM chase_cards WHERE pc_path = %s", (card['pc_path'],))
                result = cur.fetchone()
            card_id = result['id']

            # Upsert price snapshot
            cur.execute("""
                INSERT INTO chase_card_prices (
                    chase_card_id, snapshot_date,
                    raw_usd, raw_gbp, psa10_usd, psa10_gbp,
                    usd_gbp_rate, price_source, fetched_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,'pricecharting_scrape',NOW())
                ON CONFLICT (chase_card_id, snapshot_date) DO UPDATE SET
                    raw_usd      = EXCLUDED.raw_usd,
                    raw_gbp      = EXCLUDED.raw_gbp,
                    psa10_usd    = EXCLUDED.psa10_usd,
                    psa10_gbp    = EXCLUDED.psa10_gbp,
                    usd_gbp_rate = EXCLUDED.usd_gbp_rate,
                    fetched_at   = NOW()
            """, (card_id, today, card['raw_usd'], raw_gbp,
                  card['psa10_usd'], psa10_gbp, rate))

            pg.commit()

        time.sleep(SLEEP)

    # Summary
    cur.execute("SELECT COUNT(*) FROM chase_cards WHERE active = TRUE")
    total_cards = cur.fetchone()['count']
    cur.execute("SELECT COUNT(*) FROM chase_card_prices WHERE snapshot_date = %s AND raw_gbp IS NOT NULL", (today,))
    total_prices = cur.fetchone()['count']
    print(f'\nDone. Active cards: {total_cards} | Prices today: {total_prices}')

    cur.close(); pg.close()

if __name__ == '__main__':
    run()
