#!/usr/bin/env python3
"""
Rebuild chase_cards using BB tracker as single source of truth.
- Sets come from monthly_snapshots (same as BB tracker)
- Cards come from top3_chase field per set
- Prices fetched from PriceCharting by searching card name + set name
"""
import os, re, time
from datetime import date
from dotenv import load_dotenv
load_dotenv('/root/.openclaw/api/.env')

import psycopg2, psycopg2.extras
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

PG_CONN = os.getenv('DATABASE_URL')
PC_BASE = 'https://www.pricecharting.com'
FX_URL  = 'https://open.er-api.com/v6/latest/USD'
SLEEP   = 1.2

# Manual PC set slug map — covers all 44 BB tracker sets
PC_SLUGS = {
    1:  'pokemon-evolutions',
    2:  'pokemon-ultra-prism',
    3:  'pokemon-lost-thunder',
    4:  'pokemon-team-up',
    5:  'pokemon-unbroken-bonds',
    6:  'pokemon-unified-minds',
    7:  'pokemon-hidden-fates',
    8:  'pokemon-cosmic-eclipse',
    9:  'pokemon-rebel-clash',
    10: 'pokemon-darkness-ablaze',
    11: 'pokemon-champion%27s-path',
    12: 'pokemon-vivid-voltage',
    13: 'pokemon-shining-fates',
    14: 'pokemon-chilling-reign',
    15: 'pokemon-evolving-skies',
    16: 'pokemon-celebrations',
    17: 'pokemon-fusion-strike',
    18: 'pokemon-brilliant-stars',
    19: 'pokemon-astral-radiance',
    20: 'pokemon-lost-origin',
    21: 'pokemon-silver-tempest',
    22: 'pokemon-crown-zenith',
    23: 'pokemon-scarlet-%26-violet',
    24: 'pokemon-paldea-evolved',
    25: 'pokemon-obsidian-flames',
    26: 'pokemon-scarlet-%26-violet-151',
    27: 'pokemon-paradox-rift',
    28: 'pokemon-paldean-fates',
    29: 'pokemon-temporal-forces',
    30: 'pokemon-twilight-masquerade',
    31: 'pokemon-shrouded-fable',
    32: 'pokemon-stellar-crown',
    33: 'pokemon-surging-sparks',
    34: 'pokemon-prismatic-evolutions',
    36: 'pokemon-destined-rivals',
    37: 'pokemon-white-flare',
    38: 'pokemon-black-bolt',
    40: 'pokemon-phantasmal-flames',
    41: 'pokemon-ascended-heroes',
    46: 'pokemon-mega-evolution',
    56: 'pokemon-battle-styles',
    60: 'pokemon-journey-together',
    82: 'pokemon-sword-%26-shield',
    85: 'pokemon-perfect-order',
}

def get_fx_rate():
    try:
        import requests as req
        r = req.get(FX_URL, timeout=10)
        rate = r.json()['rates']['GBP']
        print(f'FX: 1 USD = {rate:.4f} GBP')
        return rate
    except:
        return 0.79

def parse_usd(text):
    if not text: return None
    cleaned = re.sub(r'[^\d.]', '', text.replace(',', ''))
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except: return None

def search_card_on_pc(card_name, set_slug):
    """Search PC set page for a card by name, return (pc_path, raw_usd, psa10_usd, card_number, image_url)"""
    url = f'{PC_BASE}/console/{set_slug}'
    try:
        r = cffi_requests.get(url, impersonate='chrome110', timeout=25)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table', id='games_table')
        if not table:
            return None

        # Normalise search name for fuzzy matching
        search = re.sub(r'[^a-z0-9 ]', '', card_name.lower()).strip()
        search_words = set(search.split())

        best_match = None
        best_score = 0

        for row in table.find_all('tr')[1:]:
            a = row.find('a', href=True)
            cols = row.find_all('td')
            if not a or len(cols) < 3:
                continue

            href = a['href']
            path = href.replace(PC_BASE, '') if href.startswith('http') else href
            name_text = a.get_text(strip=True)

            # Derive name from slug if text is blank
            if not name_text:
                slug_part = path.split('/')[-1]
                slug_part = re.sub(r'-\d+[a-z]?$', '', slug_part)
                name_text = slug_part.replace('-', ' ').replace('%26', '&').title()

            # Score match
            row_name = re.sub(r'[^a-z0-9 ]', '', name_text.lower()).strip()
            row_words = set(row_name.split())
            # Remove card numbers
            row_words = {w for w in row_words if not w.isdigit()}
            search_words_clean = {w for w in search_words if not w.isdigit()}

            if not search_words_clean:
                continue

            overlap = len(search_words_clean & row_words)
            score = overlap / len(search_words_clean)

            if score > best_score:
                best_score = score
                num_match = re.search(r'#([A-Z0-9/]+)', name_text)
                card_number = num_match.group(1) if num_match else None
                raw_usd   = parse_usd(cols[2].get_text(strip=True)) if len(cols) > 2 else None
                psa10_usd = parse_usd(cols[4].get_text(strip=True)) if len(cols) > 4 else None

                # Try to get image from card page
                best_match = {
                    'pc_path':     path,
                    'pc_name':     name_text,
                    'card_number': card_number,
                    'raw_usd':     raw_usd,
                    'psa10_usd':   psa10_usd,
                    'score':       score,
                }

        if best_match and best_match['score'] >= 0.5:
            return best_match
        return None

    except Exception as e:
        print(f'    Search error: {e}')
        return None

def get_card_image(pc_path):
    """Scrape card image from PC card page"""
    try:
        r = cffi_requests.get(PC_BASE + pc_path, impersonate='chrome110', timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        # PC card image is usually in #product_image or similar
        img = soup.find('img', id='product_image') or \
              soup.find('div', class_='product-image') and soup.find('div', class_='product-image').find('img')
        if img and img.get('src'):
            src = img['src']
            if src.startswith('//'):
                src = 'https:' + src
            return src
        return None
    except:
        return None

def run():
    pg = psycopg2.connect(PG_CONN)
    pg.cursor_factory = psycopg2.extras.RealDictCursor
    cur = pg.cursor()

    today = date.today().isoformat()
    rate  = get_fx_rate()

    # Get all BB tracker sets with top3_chase
    cur.execute("""
        SELECT s.id as set_id, s.name as set_name, ms.top3_chase
        FROM sets s
        JOIN monthly_snapshots ms ON ms.set_id = s.id
        WHERE ms.run_date = (SELECT MAX(run_date) FROM monthly_snapshots)
          AND ms.top3_chase IS NOT NULL
        ORDER BY s.id
    """)
    bb_sets = cur.fetchall()
    print(f'\nProcessing {len(bb_sets)} BB tracker sets...\n')

    # Wipe and rebuild
    cur.execute("DELETE FROM chase_card_prices")
    cur.execute("DELETE FROM chase_cards")
    pg.commit()

    processed = 0
    for bb_set in bb_sets:
        set_id   = bb_set['set_id']
        set_name = bb_set['set_name']
        top3     = bb_set['top3_chase']

        pc_slug = PC_SLUGS.get(set_id)
        if not pc_slug:
            print(f'[{set_name}] No PC slug — skipping')
            continue

        cards = [c.strip() for c in top3.split(',') if c.strip()]
        print(f'[{set_name}] ({pc_slug})')

        for rank, card_name in enumerate(cards[:3], 1):
            print(f'  #{rank} Searching: {card_name}')
            match = search_card_on_pc(card_name, pc_slug)

            if not match:
                print(f'    Not found on PC — inserting without price')
                cur.execute("""
                    INSERT INTO chase_cards (set_id, card_name, active)
                    VALUES (%s, %s, TRUE) RETURNING id
                """, (set_id, card_name))
                card_id = cur.fetchone()['id']
            else:
                print(f'    Found: {match["pc_name"]} (score={match["score"]:.2f}) raw=${match["raw_usd"]} psa10=${match["psa10_usd"]}')
                # Get image
                img_url = get_card_image(match['pc_path'])

                cur.execute("""
                    INSERT INTO chase_cards (set_id, card_name, card_number, pc_path, image_url, active)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    ON CONFLICT (pc_path) DO UPDATE SET
                        set_id=EXCLUDED.set_id, card_name=EXCLUDED.card_name,
                        card_number=EXCLUDED.card_number, image_url=EXCLUDED.image_url, active=TRUE
                    RETURNING id
                """, (set_id, card_name, match['card_number'], match['pc_path'], img_url))
                result = cur.fetchone()
                if not result:
                    cur.execute("SELECT id FROM chase_cards WHERE pc_path=%s", (match['pc_path'],))
                    result = cur.fetchone()
                card_id = result['id']

                if match['raw_usd']:
                    raw_gbp   = round(match['raw_usd']   * rate, 2)
                    psa10_gbp = round(match['psa10_usd'] * rate, 2) if match['psa10_usd'] else None
                    cur.execute("""
                        INSERT INTO chase_card_prices (
                            chase_card_id, snapshot_date,
                            raw_usd, raw_gbp, psa10_usd, psa10_gbp,
                            usd_gbp_rate, price_source, fetched_at
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,'pricecharting_scrape',NOW())
                        ON CONFLICT (chase_card_id, snapshot_date) DO UPDATE SET
                            raw_usd=EXCLUDED.raw_usd, raw_gbp=EXCLUDED.raw_gbp,
                            psa10_usd=EXCLUDED.psa10_usd, psa10_gbp=EXCLUDED.psa10_gbp
                    """, (card_id, today, match['raw_usd'], raw_gbp,
                          match['psa10_usd'], psa10_gbp, rate))

            pg.commit()
            time.sleep(SLEEP)

        processed += 1
        time.sleep(SLEEP)

    cur.execute("SELECT COUNT(*) FROM chase_cards WHERE active=TRUE")
    print(f'\nDone. Cards: {cur.fetchone()["count"]}')
    cur.close(); pg.close()

if __name__ == '__main__':
    run()
