#!/usr/bin/env python3
"""
Seed chase_cards from the BB tracker's chase_cards_json (source of truth).
Uses PokemonWizard card names and images. PC paths for pricing added separately.
Covers ALL sets in monthly_snapshots.
"""
import os, json, re
from dotenv import load_dotenv
load_dotenv('/root/.openclaw/api/.env')
import psycopg2, psycopg2.extras

pg  = psycopg2.connect(os.getenv('DATABASE_URL'))
pg.cursor_factory = psycopg2.extras.RealDictCursor
cur = pg.cursor()

# Wipe and re-seed
cur.execute('DELETE FROM chase_card_prices')
cur.execute('DELETE FROM chase_cards')
pg.commit()

# Get all sets that appear in monthly_snapshots (BB tracker source of truth)
cur.execute('''
    SELECT DISTINCT s.id, s.name, s.era, s.chase_cards_json
    FROM sets s
    JOIN monthly_snapshots ms ON ms.set_id = s.id
    ORDER BY s.name
''')
sets = cur.fetchall()
print(f'BB tracker sets: {len(sets)}')

def clean_name(name):
    # Strip card number suffix e.g. "Duskull - 068/064" -> "Duskull"
    name = re.sub(r'\s*-\s*\d+/\d+\s*$', '', name).strip()
    # Strip rarity suffix in parens e.g. "Charizard VMAX (Alternate Art Secret)"
    # Keep as-is — useful info
    return name

inserted = skipped = no_json = 0
for s in sets:
    cj = s['chase_cards_json']
    if not cj:
        no_json += 1
        print(f'  [NO JSON] {s["name"]}')
        continue

    cards = json.loads(cj) if isinstance(cj, str) else cj
    print(f'  [{s["name"]}] {len(cards)} cards')

    for i, card in enumerate(cards[:3]):  # max 3 per set
        name  = clean_name(card.get('name', ''))
        image = card.get('image', None)
        if not name:
            continue
        try:
            cur.execute('''
                INSERT INTO chase_cards (set_id, card_name, image_url, active)
                VALUES (%s, %s, %s, TRUE)
            ''', (s['id'], name, image))
            inserted += 1
        except Exception as e:
            print(f'    SKIP {name}: {e}')
            pg.rollback()
            skipped += 1
            continue
        pg.commit()

cur.execute('SELECT COUNT(*) FROM chase_cards')
total = cur.fetchone()['count']
print(f'\nDone. Inserted: {inserted} | Skipped: {skipped} | No JSON: {no_json} | Total: {total}')
cur.close(); pg.close()
