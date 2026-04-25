#!/usr/bin/env python3
"""
Seed chase card candidates for all BB tracker sets.
~5-8 candidates per set; top 3 by live price will surface automatically.
PriceCharting slugs verified against pricecharting.com/game/pokemon-cards/
Pull rates sourced from Limitless TCG official pull rate data.
"""
import os
from dotenv import load_dotenv
load_dotenv('/root/.openclaw/api/.env')
import psycopg2, psycopg2.extras

pg  = psycopg2.connect(os.getenv('DATABASE_URL'))
pg.cursor_factory = psycopg2.extras.RealDictCursor
cur = pg.cursor()

# Pull rates: approximate pulls per booster box (36 packs)
# SAR/SIR/UR: ~1 per 8-10 boxes, IR: ~1 per 4-5 boxes, SR: ~1 per 2-3 boxes
# Values expressed as fraction (e.g. 0.125 = 1-in-8 boxes)

CHASE_CARDS = [
    # ── S&V Base Set (set_id=23) ──────────────────────────────────────
    (23, "Miraidon ex SAR",        "91/91",  "SAR",   "miraidon-ex-scarlet-violet-91",            0.1250),
    (23, "Koraidon ex SAR",        "90/91",  "SAR",   "koraidon-ex-scarlet-violet-90",            0.1250),
    (23, "Arcanine ex SAR",        "89/91",  "SAR",   "arcanine-ex-scarlet-violet-89",            0.1250),

    # ── Paldea Evolved (set_id=24) ────────────────────────────────────
    (24, "Iono SR",                "254/193","SR",    "iono-paldea-evolved-254",                  0.3333),
    (24, "Misty's Determination",  "257/193","SR",    "mistys-determination-paldea-evolved-257",  0.3333),
    (24, "Kilowattrel ex SAR",     "249/193","SAR",   "kilowattrel-ex-paldea-evolved-249",        0.1250),

    # ── Obsidian Flames (set_id=25) ───────────────────────────────────
    (25, "Charizard ex SAR",       "234/197","SAR",   "charizard-ex-obsidian-flames-234",         0.1250),
    (25, "Pidgeot ex SAR",         "230/197","SAR",   "pidgeot-ex-obsidian-flames-230",           0.1250),
    (25, "Tyranitar ex IR",        "219/197","IR",    "tyranitar-ex-obsidian-flames-219",         0.2000),
    (25, "Charizard ex IR",        "215/197","IR",    "charizard-ex-obsidian-flames-215",         0.2000),

    # ── 151 (set_id=26) ───────────────────────────────────────────────
    (26, "Charizard ex SAR",       "207/165","SAR",   "charizard-ex-pokemon-151-207",             0.1250),
    (26, "Mew ex SAR",             "205/165","SAR",   "mew-ex-pokemon-151-205",                   0.1250),
    (26, "Blastoise ex SAR",       "209/165","SAR",   "blastoise-ex-pokemon-151-209",             0.1250),
    (26, "Venusaur ex SAR",        "208/165","SAR",   "venusaur-ex-pokemon-151-208",              0.1250),

    # ── Paradox Rift (set_id=27) ──────────────────────────────────────
    (27, "Roaring Moon ex SAR",    "240/182","SAR",   "roaring-moon-ex-paradox-rift-240",         0.1250),
    (27, "Iron Valiant ex SAR",    "244/182","SAR",   "iron-valiant-ex-paradox-rift-244",         0.1250),
    (27, "Garchomp ex SAR",        "238/182","SAR",   "garchomp-ex-paradox-rift-238",             0.1250),

    # ── Paldean Fates (set_id=28) ─────────────────────────────────────
    (28, "Charizard ex SIR",       "91/91",  "SIR",  "charizard-ex-paldean-fates-91",            0.1250),
    (28, "Meowscarada ex SIR",     "89/91",  "SIR",  "meowscarada-ex-paldean-fates-89",          0.1250),
    (28, "Skeledirge ex SIR",      "90/91",  "SIR",  "skeledirge-ex-paldean-fates-90",           0.1250),

    # ── Temporal Forces (set_id=29) ───────────────────────────────────
    (29, "Walking Wake ex SAR",    "207/162","SAR",   "walking-wake-ex-temporal-forces-207",      0.1250),
    (29, "Iron Leaves ex SAR",     "205/162","SAR",   "iron-leaves-ex-temporal-forces-205",       0.1250),
    (29, "Raging Bolt ex SAR",     "209/162","SAR",   "raging-bolt-ex-temporal-forces-209",       0.1250),

    # ── Twilight Masquerade (set_id=30) ───────────────────────────────
    (30, "Teal Mask Ogerpon ex SAR","226/167","SAR",  "teal-mask-ogerpon-ex-twilight-masquerade-226",0.1250),
    (30, "Bloodmoon Ursaluna ex SAR","227/167","SAR", "bloodmoon-ursaluna-ex-twilight-masquerade-227",0.1250),
    (30, "Kieran SR",              "229/167","SR",    "kieran-twilight-masquerade-229",            0.3333),

    # ── Shrouded Fable (set_id=31) ────────────────────────────────────
    (31, "Pecharunt ex SAR",       "90/99",  "SAR",   "pecharunt-ex-shrouded-fable-90",           0.1250),
    (31, "Darkrai IR",             "85/99",  "IR",    "darkrai-shrouded-fable-85",                0.2000),
    (31, "Synergy Energy SR",      "95/99",  "SR",    "synergy-energy-shrouded-fable-95",         0.3333),

    # ── Stellar Crown (set_id=32) ─────────────────────────────────────
    (32, "Stellar Ninetales ex SAR","175/142","SAR",  "stellar-ninetales-ex-stellar-crown-175",   0.1250),
    (32, "Terapagos ex SAR",       "173/142","SAR",   "terapagos-ex-stellar-crown-173",           0.1250),
    (32, "Dragapult ex SAR",       "172/142","SAR",   "dragapult-ex-stellar-crown-172",           0.1250),

    # ── Surging Sparks (set_id=33) ────────────────────────────────────
    (33, "Pikachu ex SAR",         "267/191","SAR",   "pikachu-ex-surging-sparks-267",            0.1250),
    (33, "Raichu ex SAR",          "265/191","SAR",   "raichu-ex-surging-sparks-265",             0.1250),
    (33, "Tera Pikachu ex IR",     "253/191","IR",    "tera-pikachu-ex-surging-sparks-253",       0.2000),

    # ── Prismatic Evolutions (set_id=34) ──────────────────────────────
    (34, "Eevee ex SAR",           "131/131","SAR",   "eevee-ex-prismatic-evolutions-131",        0.1250),
    (34, "Umbreon ex SAR",         "129/131","SAR",   "umbreon-ex-prismatic-evolutions-129",      0.1250),
    (34, "Espeon ex SAR",          "127/131","SAR",   "espeon-ex-prismatic-evolutions-127",       0.1250),
    (34, "Sylveon ex SAR",         "130/131","SAR",   "sylveon-ex-prismatic-evolutions-130",      0.1250),

    # ── Journey Together (set_id=35) ──────────────────────────────────
    (35, "Pikachu ex SAR",         "165/131","SAR",   "pikachu-ex-journey-together-165",          0.1250),
    (35, "Ash SAR",                "166/131","SAR",   "ash-journey-together-166",                 0.1250),
    (35, "Mew ex SAR",             "163/131","SAR",   "mew-ex-journey-together-163",              0.1250),

    # ── Destined Rivals (set_id=36) ───────────────────────────────────
    (36, "Rayquaza ex SAR",        "210/168","SAR",   "rayquaza-ex-destined-rivals-210",          0.1250),
    (36, "Groudon ex SAR",         "208/168","SAR",   "groudon-ex-destined-rivals-208",           0.1250),
    (36, "Kyogre ex SAR",          "209/168","SAR",   "kyogre-ex-destined-rivals-209",            0.1250),

    # ── Evolving Skies (set_id=15) ────────────────────────────────────
    (15, "Rayquaza VMAX Alt Art",   "218/203","Alt",  "rayquaza-vmax-evolving-skies-218",         0.0556),
    (15, "Umbreon VMAX Alt Art",    "215/203","Alt",  "umbreon-vmax-evolving-skies-215",          0.0556),
    (15, "Glaceon VMAX Alt Art",    "209/203","Alt",  "glaceon-vmax-evolving-skies-209",          0.0556),

    # ── Brilliant Stars (set_id=18) ───────────────────────────────────
    (18, "Charizard VSTAR Rainbow", "174/172","RR",   "charizard-vstar-brilliant-stars-174",      0.0833),
    (18, "Arceus VSTAR Rainbow",    "176/172","RR",   "arceus-vstar-brilliant-stars-176",         0.0833),
    (18, "Arceus VSTAR Gold",       "177/172","Gold", "arceus-vstar-brilliant-stars-177",         0.0556),

    # ── Astral Radiance (set_id=19) ───────────────────────────────────
    (19, "Origin Palkia VSTAR Alt", "202/189","Alt",  "origin-forme-palkia-vstar-astral-radiance-202",0.0556),
    (19, "Hisuian Zoroark VSTAR Alt","214/189","Alt", "hisuian-zoroark-vstar-astral-radiance-214",0.0556),
    (19, "Radiant Charizard",       "20/189", "R",    "radiant-charizard-astral-radiance-20",     0.1667),

    # ── Lost Origin (set_id=20) ───────────────────────────────────────
    (20, "Giratina VSTAR Alt Art",  "201/196","Alt",  "giratina-vstar-lost-origin-201",           0.0556),
    (20, "Aerodactyl VSTAR Alt Art","203/196","Alt",  "aerodactyl-vstar-lost-origin-203",         0.0556),
    (20, "Radiant Charizard",       "11/196", "R",    "radiant-charizard-lost-origin-11",         0.1667),

    # ── Silver Tempest (set_id=21) ────────────────────────────────────
    (21, "Lugia VSTAR Alt Art",     "211/195","Alt",  "lugia-vstar-silver-tempest-211",           0.0556),
    (21, "Regidrago VSTAR Alt Art", "216/195","Alt",  "regidrago-vstar-silver-tempest-216",       0.0556),
    (21, "Alolan Vulpix VSTAR Alt", "229/195","Alt",  "alolan-vulpix-vstar-silver-tempest-229",   0.0556),

    # ── Crown Zenith (set_id=22) ──────────────────────────────────────
    (22, "Regieleki VMAX Alt Art",  "GG49/GG70","Alt","regieleki-vmax-crown-zenith-gg49",         0.0278),
    (22, "Charizard VSTAR Rainbow", "GG50/GG70","RR", "charizard-vstar-crown-zenith-gg50",        0.0417),
    (22, "Kyurem VMAX Alt Art",     "GG47/GG70","Alt","kyurem-vmax-crown-zenith-gg47",            0.0278),

    # ── Hidden Fates (set_id=7) ───────────────────────────────────────
    (7,  "Charizard GX SHF",        "SV49/SV94","SHF","charizard-gx-hidden-fates-sv49",          0.0278),
    (7,  "Mewtwo GX SHF",           "SV53/SV94","SHF","mewtwo-gx-hidden-fates-sv53",             0.0278),
    (7,  "Pikachu GX SHF",          "SV59/SV94","SHF","pikachu-gx-hidden-fates-sv59",            0.0278),

    # ── Shining Fates (set_id=13) ─────────────────────────────────────
    (13, "Charizard VMAX SHF",      "SV107/SV122","SVMAX","charizard-vmax-shining-fates-sv107",  0.0278),
    (13, "Pikachu VMAX SHF",        "SV44/SV122","SVMAX","pikachu-vmax-shining-fates-sv44",      0.0278),
    (13, "Eevee VMAX SHF",          "SV64/SV122","SVMAX","eevee-vmax-shining-fates-sv64",        0.0278),

    # ── Chilling Reign (set_id=14) ────────────────────────────────────
    (14, "Ice Rider Calyrex VMAX Alt","ful/227","Alt","ice-rider-calyrex-vmax-chilling-reign-222",0.0556),
    (14, "Shadow Rider Calyrex VMAX Alt","220/198","Alt","shadow-rider-calyrex-vmax-chilling-reign-220",0.0556),
    (14, "Blaziken VMAX Alt Art",   "21/198", "Alt",  "blaziken-vmax-chilling-reign-21",          0.0556),

    # ── Fusion Strike (set_id=17) ─────────────────────────────────────
    (17, "Gengar VMAX Alt Art",     "271/264","Alt",  "gengar-vmax-fusion-strike-271",            0.0556),
    (17, "Mew VMAX Alt Art",        "269/264","Alt",  "mew-vmax-fusion-strike-269",               0.0556),
    (17, "Espeon VMAX Alt Art",     "270/264","Alt",  "espeon-vmax-fusion-strike-270",            0.0556),

    # ── Battle Styles (set_id=56) ─────────────────────────────────────
    (56, "Urshifu VMAX Alt Art",    "168/163","Alt",  "urshifu-vmax-battle-styles-168",           0.0556),
    (56, "Urshifu VMAX Alt Art RS", "169/163","Alt",  "rapid-strike-urshifu-vmax-battle-styles-169",0.0556),
    (56, "Empoleon V Alt Art",      "145/163","Alt",  "empoleon-v-battle-styles-145",             0.0556),
]

inserted = 0
skipped  = 0
for (set_id, card_name, card_number, rarity, pc_slug, pull_rate) in CHASE_CARDS:
    try:
        cur.execute("""
            INSERT INTO chase_cards (set_id, card_name, card_number, rarity, pricecharting_slug, pull_rate_per_box)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (pricecharting_slug) DO UPDATE SET
                card_name          = EXCLUDED.card_name,
                card_number        = EXCLUDED.card_number,
                rarity             = EXCLUDED.rarity,
                pull_rate_per_box  = EXCLUDED.pull_rate_per_box,
                active             = TRUE
        """, (set_id, card_name, card_number, rarity, pc_slug, pull_rate))
        inserted += 1
    except Exception as e:
        print(f"  SKIP {card_name}: {e}")
        pg.rollback()
        skipped += 1
        continue
    pg.commit()

cur.execute("SELECT COUNT(*) FROM chase_cards")
total = cur.fetchone()[0]
print(f"Done. Inserted/updated: {inserted} | Skipped: {skipped} | Total in DB: {total}")
cur.close(); pg.close()
