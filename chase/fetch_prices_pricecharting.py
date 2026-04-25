#!/usr/bin/env python3
"""
Chase card price fetcher — PriceCharting API.
Fetches raw (loose-price) and PSA 10 (graded-price) for all active chase cards.
Runs weekly via cron. Top 3 per set determined at query time by raw_gbp DESC.
"""
import os, sys, time
from datetime import date
from dotenv import load_dotenv
load_dotenv('/root/.openclaw/api/.env')
import psycopg2, psycopg2.extras, requests

PG_CONN    = os.getenv('DATABASE_URL')
PC_API_KEY = os.getenv('PRICECHARTING_API_KEY', '')
PC_BASE    = 'https://www.pricecharting.com/api/product'
FX_URL     = 'https://open.er-api.com/v6/latest/USD'

def get_fx_rate():
    try:
        r = requests.get(FX_URL, timeout=10)
        rate = r.json()['rates']['GBP']
        print(f'  FX rate: 1 USD = {rate:.4f} GBP')
        return rate
    except Exception as e:
        print(f'  FX fetch failed: {e} — using fallback 0.79')
        return 0.79

def fetch_pc(slug, rate):
    if not PC_API_KEY:
        print('  No PRICECHARTING_API_KEY — skipping')
        return None
    try:
        url  = f'{PC_BASE}?id={slug}&status=sold&key={PC_API_KEY}'
        r    = requests.get(url, timeout=15)
        data = r.json()

        if 'status' in data and data['status'] == 'error':
            print(f'    PC error: {data.get("error", "unknown")}')
            return None

        raw_usd   = (data.get('loose-price') or 0) / 100
        psa10_usd = (data.get('graded-price') or 0) / 100

        if raw_usd == 0 and psa10_usd == 0:
            print(f'    No price data')
            return None

        raw_gbp   = round(raw_usd   * rate, 2)
        psa10_gbp = round(psa10_usd * rate, 2)
        print(f'    Raw: ${raw_usd:.2f} / £{raw_gbp:.2f} | PSA10: ${psa10_usd:.2f} / £{psa10_gbp:.2f}')
        return raw_usd, raw_gbp, psa10_usd, psa10_gbp

    except Exception as e:
        print(f'    Fetch failed: {e}')
        return None

def run():
    if not PC_API_KEY:
        print('ERROR: PRICECHARTING_API_KEY not set in .env'); sys.exit(1)

    pg  = psycopg2.connect(PG_CONN)
    pg.cursor_factory = psycopg2.extras.RealDictCursor
    cur = pg.cursor()

    today = date.today().isoformat()
    rate  = get_fx_rate()

    cur.execute("""
        SELECT cc.id, cc.card_name, cc.pricecharting_slug, s.name AS set_name
        FROM   chase_cards cc
        JOIN   sets s ON s.id = cc.set_id
        WHERE  cc.active = TRUE
          AND  cc.pricecharting_slug IS NOT NULL
        ORDER  BY s.name, cc.card_name
    """)
    cards = cur.fetchall()
    print(f'\nFetching prices for {len(cards)} chase cards...\n')

    updated = skipped = no_data = 0

    for card in cards:
        print(f'  [{card["set_name"]}] {card["card_name"]}')
        result = fetch_pc(card['pricecharting_slug'], rate)

        if not result:
            # Insert placeholder so we track attempt date
            cur.execute("""
                INSERT INTO chase_card_prices (chase_card_id, snapshot_date, usd_gbp_rate, price_source)
                VALUES (%s, %s, %s, 'pricecharting')
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
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,'pricecharting',NOW())
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
        time.sleep(0.8)  # respect API rate limits

    print(f'\nDone. Updated: {updated} | No data: {no_data}')
    cur.close(); pg.close()

if __name__ == '__main__':
    run()
