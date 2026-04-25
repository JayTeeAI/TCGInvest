#!/usr/bin/env python3
import os, sys
from dotenv import load_dotenv
load_dotenv('/root/.openclaw/api/.env')
import psycopg2

pg  = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = pg.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS chase_cards (
    id                   SERIAL PRIMARY KEY,
    set_id               INT NOT NULL REFERENCES sets(id) ON DELETE CASCADE,
    card_name            TEXT NOT NULL,
    card_number          TEXT,
    rarity               TEXT,
    pricecharting_slug   TEXT UNIQUE,
    pull_rate_per_box    NUMERIC(8,5),
    image_url            TEXT,
    active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS chase_card_prices (
    id              SERIAL PRIMARY KEY,
    chase_card_id   INT NOT NULL REFERENCES chase_cards(id) ON DELETE CASCADE,
    snapshot_date   DATE NOT NULL,
    raw_usd         NUMERIC(10,2),
    raw_gbp         NUMERIC(10,2),
    psa10_usd       NUMERIC(10,2),
    psa10_gbp       NUMERIC(10,2),
    usd_gbp_rate    NUMERIC(8,6),
    price_source    TEXT NOT NULL DEFAULT 'pricecharting',
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(chase_card_id, snapshot_date)
);
""")

cur.execute("CREATE INDEX IF NOT EXISTS idx_ccp_card_date ON chase_card_prices(chase_card_id, snapshot_date DESC);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_set ON chase_cards(set_id) WHERE active = TRUE;")

pg.commit()
cur.close(); pg.close()
print("Migration complete.")
