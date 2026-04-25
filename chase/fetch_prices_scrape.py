#!/usr/bin/env python3
"""
Chase card price scraper — PriceCharting web scrape.
Extracts raw (Ungraded) and PSA 10 prices directly from card pages.
Runs weekly via cron. Top 3 per set determined at query time by raw_gbp DESC.
Uses curl_cffi to impersonate Chrome (same pattern as dawnglare fetcher).
"""
import os, sys, time, re
from datetime import date
from dotenv import load_dotenv
load_dotenv('/root/.openclaw/api/.env')

import psycopg2, psycopg2.extras
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

PG_CONN  = os.getenv('DATABASE_URL')
FX_URL   = 'https://open.er-api.com/v6/latest/USD'
PC_BASE  = 'https://www.pricecharting.com'
SLEEP    = 1.2   # seconds between requests

def get_fx_rate():
    try:
        import requests
        r    = requests.get(FX_URL, timeout=10)
        rate = r.json()['rates']['GBP']
        print(f'  FX rate: 1 USD = {rate:.4f} GBP')
        return rate
    except Exception as e:
        print(f'  FX fetch failed: {e} — using fallback 0.79')
        return 0.79

def parse_usd(text):
    """'$1,234.56' -> 1234.56, None if unparseable"""
    if not text:
        return None
    cleaned = re.sub(r'[^\d.]', '', text.replace(',', ''))
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None

def scrape_card(pc_path, rate):
    """
    pc_path: e.g. '/game/pokemon-obsidian-flames/charizard-ex-234'
    Returns (raw_usd, raw_gbp, psa10_usd, psa10_gbp) or None
    """
    url = PC_BASE + pc_path
    try:
        r    = cffi_requests.get(url, impersonate='chrome110', timeout=25)
        if r.status_code != 200:
            print(f'    HTTP {r.status_code}')
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        raw_td   = soup.find('td', id='used_price')
        psa10_td = soup.find('td', id='manual_only_price')

        raw_span   = raw_td.find('span',   class_='price') if raw_td   else None
        psa10_span = psa10_td.find('span', class_='price') if psa10_td else None

        raw_usd   = parse_usd(raw_span.get_text(strip=True)   if raw_span   else None)
        psa10_usd = parse_usd(psa10_span.get_text(strip=True) if psa10_span else None)

        if raw_usd is None and psa10_usd is None:
            print(f'    No price data at {url}')
            return None

        raw_gbp   = round(raw_usd   * rate, 2) if raw_usd   else None
        psa10_gbp = round(psa10_usd * rate, 2) if psa10_usd else None

        print(f'    Raw: ${raw_usd} / £{raw_gbp}  |  PSA10: ${psa10_usd} / £{psa10_gbp}')
        return raw_usd, raw_gbp, psa10_usd, psa10_gbp

    except Exception as e:
        print(f'    Scrape failed: {e}')
        return None

def run():
    pg  = psycopg2.connect(PG_CONN)
    pg.cursor_factory = psycopg2.extras.RealDictCursor
    cur = pg.cursor()

    today = date.today().isoformat()
    rate  = get_fx_rate()

    cur.execute("""
        SELECT cc.id, cc.card_name, cc.pc_path, s.name AS set_name
        FROM   chase_cards cc
        JOIN   sets s ON s.id = cc.set_id
        WHERE  cc.active = TRUE
          AND  cc.pc_path IS NOT NULL
        ORDER  BY s.name, cc.card_name
    """)
    cards = cur.fetchall()
    print(f'\nScraping prices for {len(cards)} chase cards...\n')

    updated = no_data = 0

    for card in cards:
        print(f'  [{card["set_name"]}] {card["card_name"]}')
        result = scrape_card(card['pc_path'], rate)

        if not result:
            cur.execute("""
                INSERT INTO chase_card_prices (chase_card_id, snapshot_date, usd_gbp_rate, price_source)
                VALUES (%s, %s, %s, 'pricecharting_scrape')
                ON CONFLICT (chase_card_id, snapshot_date) DO NOTHING
            """, (card['id'], today, rate))
            no_data += 1
        else:
            raw_usd, raw_gbp, psa10_usd, psa10_gbp = result
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
            """, (card['id'], today, raw_usd, raw_gbp, psa10_usd, psa10_gbp, rate))
            updated += 1

        pg.commit()
        time.sleep(SLEEP)

    print(f'\nDone. Updated: {updated} | No data: {no_data}')
    cur.close(); pg.close()

if __name__ == '__main__':
    run()
