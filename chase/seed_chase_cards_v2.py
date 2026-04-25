#!/usr/bin/env python3
"""
Seed chase cards with verified PriceCharting URL paths.
pc_path = everything after pricecharting.com
Pull rates from Limitless TCG (pulls per booster box of 36 packs).
"""
import os
from dotenv import load_dotenv
load_dotenv('/root/.openclaw/api/.env')
import psycopg2, psycopg2.extras

pg  = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = pg.cursor()

# Wipe and re-seed cleanly
cur.execute("DELETE FROM chase_card_prices")
cur.execute("DELETE FROM chase_cards")

# (set_id, card_name, card_number, rarity, pc_path, pull_rate_per_box)
# pull_rate = fraction of boxes yielding this card (e.g. 0.125 = 1-in-8 boxes)
CARDS = [
    # ── Obsidian Flames (25) ──────────────────────────────────────────
    (25, "Charizard ex SAR",      "234/197", "SAR", "/game/pokemon-obsidian-flames/charizard-ex-234",       0.1250),
    (25, "Pidgeot ex SAR",        "230/197", "SAR", "/game/pokemon-obsidian-flames/pidgeot-ex-230",         0.1250),
    (25, "Charizard ex IR",       "215/197", "IR",  "/game/pokemon-obsidian-flames/charizard-ex-215",       0.2000),
    (25, "Tyranitar ex IR",       "219/197", "IR",  "/game/pokemon-obsidian-flames/tyranitar-ex-219",       0.2000),

    # ── 151 (26) ──────────────────────────────────────────────────────
    (26, "Charizard ex SAR",      "199/165", "SAR", "/game/pokemon-scarlet-%26-violet-151/charizard-ex-199",0.1250),
    (26, "Mew ex SAR",            "205/165", "SAR", "/game/pokemon-scarlet-%26-violet-151/mew-ex-205",      0.1250),
    (26, "Blastoise ex SAR",      "200/165", "SAR", "/game/pokemon-scarlet-%26-violet-151/blastoise-ex-200",0.1250),
    (26, "Venusaur ex SAR",       "198/165", "SAR", "/game/pokemon-scarlet-%26-violet-151/venusaur-ex-198", 0.1250),

    # ── Paldea Evolved (24) ───────────────────────────────────────────
    (24, "Iono SR",               "254/193", "SR",  "/game/pokemon-paldea-evolved/iono-254",                0.3333),
    (24, "Kilowattrel ex SAR",    "249/193", "SAR", "/game/pokemon-paldea-evolved/kilowattrel-ex-249",      0.1250),
    (24, "Sylveon ex SAR",        "248/193", "SAR", "/game/pokemon-paldea-evolved/sylveon-ex-248",          0.1250),

    # ── Paradox Rift (27) ─────────────────────────────────────────────
    (27, "Roaring Moon ex SAR",   "240/182", "SAR", "/game/pokemon-paradox-rift/roaring-moon-ex-240",       0.1250),
    (27, "Iron Valiant ex SAR",   "244/182", "SAR", "/game/pokemon-paradox-rift/iron-valiant-ex-244",       0.1250),
    (27, "Garchomp ex SAR",       "238/182", "SAR", "/game/pokemon-paradox-rift/garchomp-ex-238",           0.1250),

    # ── Paldean Fates (28) ────────────────────────────────────────────
    (28, "Charizard ex SIR",      "234/91",  "SIR", "/game/pokemon-paldean-fates/charizard-ex-234",         0.1250),
    (28, "Meowscarada ex SIR",    "230/91",  "SIR", "/game/pokemon-paldean-fates/meowscarada-ex-230",       0.1250),
    (28, "Skeledirge ex SIR",     "232/91",  "SIR", "/game/pokemon-paldean-fates/skeledirge-ex-232",        0.1250),

    # ── Temporal Forces (29) ──────────────────────────────────────────
    (29, "Walking Wake ex SAR",   "207/162", "SAR", "/game/pokemon-temporal-forces/walking-wake-ex-207",    0.1250),
    (29, "Raging Bolt ex SAR",    "209/162", "SAR", "/game/pokemon-temporal-forces/raging-bolt-ex-209",     0.1250),
    (29, "Iron Leaves ex SAR",    "205/162", "SAR", "/game/pokemon-temporal-forces/iron-leaves-ex-205",     0.1250),

    # ── Twilight Masquerade (30) ──────────────────────────────────────
    (30, "Teal Mask Ogerpon ex SAR","226/167","SAR", "/game/pokemon-twilight-masquerade/teal-mask-ogerpon-ex-226",0.1250),
    (30, "Bloodmoon Ursaluna ex SAR","227/167","SAR","/game/pokemon-twilight-masquerade/bloodmoon-ursaluna-ex-227",0.1250),
    (30, "Kieran SR",             "229/167", "SR",  "/game/pokemon-twilight-masquerade/kieran-229",         0.3333),

    # ── Shrouded Fable (31) ───────────────────────────────────────────
    (31, "Pecharunt ex SAR",      "90/99",   "SAR", "/game/pokemon-shrouded-fable/pecharunt-ex-90",         0.1250),
    (31, "Darkrai IR",            "85/99",   "IR",  "/game/pokemon-shrouded-fable/darkrai-85",              0.2000),
    (31, "Synergy Energy SR",     "95/99",   "SR",  "/game/pokemon-shrouded-fable/synergy-energy-95",       0.3333),

    # ── Stellar Crown (32) ────────────────────────────────────────────
    (32, "Stellar Ninetales ex SAR","175/142","SAR", "/game/pokemon-stellar-crown/ninetales-ex-175",         0.1250),
    (32, "Terapagos ex SAR",      "173/142", "SAR", "/game/pokemon-stellar-crown/terapagos-ex-173",         0.1250),
    (32, "Dragapult ex SAR",      "172/142", "SAR", "/game/pokemon-stellar-crown/dragapult-ex-172",         0.1250),

    # ── Surging Sparks (33) ───────────────────────────────────────────
    (33, "Pikachu ex SAR",        "267/191", "SAR", "/game/pokemon-surging-sparks/pikachu-ex-267",          0.1250),
    (33, "Raichu ex SAR",         "265/191", "SAR", "/game/pokemon-surging-sparks/raichu-ex-265",           0.1250),
    (33, "Tera Pikachu ex IR",    "253/191", "IR",  "/game/pokemon-surging-sparks/pikachu-ex-253",          0.2000),

    # ── Prismatic Evolutions (34) ─────────────────────────────────────
    (34, "Eevee ex SAR",          "131/131", "SAR", "/game/pokemon-prismatic-evolutions/eevee-ex-131",      0.1250),
    (34, "Umbreon ex SAR",        "129/131", "SAR", "/game/pokemon-prismatic-evolutions/umbreon-ex-129",    0.1250),
    (34, "Espeon ex SAR",         "127/131", "SAR", "/game/pokemon-prismatic-evolutions/espeon-ex-127",     0.1250),
    (34, "Sylveon ex SAR",        "130/131", "SAR", "/game/pokemon-prismatic-evolutions/sylveon-ex-130",    0.1250),

    # ── Journey Together (35) ─────────────────────────────────────────
    (35, "Pikachu ex SAR",        "165/131", "SAR", "/game/pokemon-journey-together/pikachu-ex-165",        0.1250),
    (35, "Ash SAR",               "166/131", "SAR", "/game/pokemon-journey-together/ash-166",               0.1250),
    (35, "Mew ex SAR",            "163/131", "SAR", "/game/pokemon-journey-together/mew-ex-163",            0.1250),

    # ── Destined Rivals (36) ──────────────────────────────────────────
    (36, "Rayquaza ex SAR",       "210/168", "SAR", "/game/pokemon-destined-rivals/rayquaza-ex-210",        0.1250),
    (36, "Groudon ex SAR",        "208/168", "SAR", "/game/pokemon-destined-rivals/groudon-ex-208",         0.1250),
    (36, "Kyogre ex SAR",         "209/168", "SAR", "/game/pokemon-destined-rivals/kyogre-ex-209",          0.1250),

    # ── Evolving Skies (15) ───────────────────────────────────────────
    (15, "Rayquaza VMAX Alt Art", "218/203", "Alt", "/game/pokemon-evolving-skies/rayquaza-vmax-218",       0.0556),
    (15, "Umbreon VMAX Alt Art",  "215/203", "Alt", "/game/pokemon-evolving-skies/umbreon-vmax-215",        0.0556),
    (15, "Glaceon VMAX Alt Art",  "209/203", "Alt", "/game/pokemon-evolving-skies/glaceon-vmax-209",        0.0556),

    # ── Brilliant Stars (18) ──────────────────────────────────────────
    (18, "Charizard VSTAR Rainbow","174/172","RR",  "/game/pokemon-brilliant-stars/charizard-vstar-174",    0.0833),
    (18, "Arceus VSTAR Rainbow",  "176/172", "RR",  "/game/pokemon-brilliant-stars/arceus-vstar-176",       0.0833),
    (18, "Arceus VSTAR Gold",     "177/172", "Gold","/game/pokemon-brilliant-stars/arceus-vstar-177",       0.0556),

    # ── Astral Radiance (19) ──────────────────────────────────────────
    (19, "Origin Palkia VSTAR Alt","202/189","Alt",  "/game/pokemon-astral-radiance/origin-forme-palkia-vstar-202",0.0556),
    (19, "Hisuian Zoroark VSTAR Alt","214/189","Alt","/game/pokemon-astral-radiance/hisuian-zoroark-vstar-214",0.0556),
    (19, "Radiant Charizard",     "20/189",  "R",   "/game/pokemon-astral-radiance/radiant-charizard-20",  0.1667),

    # ── Lost Origin (20) ──────────────────────────────────────────────
    (20, "Giratina VSTAR Alt Art","201/196", "Alt", "/game/pokemon-lost-origin/giratina-vstar-201",         0.0556),
    (20, "Aerodactyl VSTAR Alt",  "203/196", "Alt", "/game/pokemon-lost-origin/aerodactyl-vstar-203",       0.0556),
    (20, "Radiant Charizard",     "11/196",  "R",   "/game/pokemon-lost-origin/radiant-charizard-11",       0.1667),

    # ── Silver Tempest (21) ───────────────────────────────────────────
    (21, "Lugia VSTAR Alt Art",   "211/195", "Alt", "/game/pokemon-silver-tempest/lugia-vstar-211",         0.0556),
    (21, "Regidrago VSTAR Alt",   "216/195", "Alt", "/game/pokemon-silver-tempest/regidrago-vstar-216",     0.0556),
    (21, "Alolan Vulpix VSTAR Alt","229/195","Alt",  "/game/pokemon-silver-tempest/alolan-vulpix-vstar-229", 0.0556),

    # ── Crown Zenith (22) ─────────────────────────────────────────────
    (22, "Regieleki VMAX Alt Art","GG49/GG70","Alt", "/game/pokemon-crown-zenith/regieleki-vmax-gg49",      0.0278),
    (22, "Charizard VSTAR Rainbow","GG50/GG70","RR", "/game/pokemon-crown-zenith/charizard-vstar-gg50",     0.0417),
    (22, "Kyurem VMAX Alt Art",   "GG47/GG70","Alt", "/game/pokemon-crown-zenith/kyurem-vmax-gg47",         0.0278),

    # ── Hidden Fates (7) ──────────────────────────────────────────────
    (7,  "Charizard GX SHF",      "SV49/SV94","SHF","/game/pokemon-hidden-fates/charizard-gx-sv49",        0.0278),
    (7,  "Mewtwo GX SHF",         "SV53/SV94","SHF","/game/pokemon-hidden-fates/mewtwo-gx-sv53",           0.0278),
    (7,  "Pikachu GX SHF",        "SV59/SV94","SHF","/game/pokemon-hidden-fates/pikachu-gx-sv59",          0.0278),

    # ── Shining Fates (13) ────────────────────────────────────────────
    (13, "Charizard VMAX SHF",    "SV107/122","SVMAX","/game/pokemon-shining-fates/charizard-vmax-sv107",   0.0278),
    (13, "Pikachu VMAX SHF",      "SV44/122", "SVMAX","/game/pokemon-shining-fates/pikachu-vmax-sv44",     0.0278),
    (13, "Eevee VMAX SHF",        "SV64/122", "SVMAX","/game/pokemon-shining-fates/eevee-vmax-sv64",       0.0278),

    # ── Chilling Reign (14) ───────────────────────────────────────────
    (14, "Ice Rider Calyrex VMAX Alt","222/198","Alt","/game/pokemon-chilling-reign/ice-rider-calyrex-vmax-222",0.0556),
    (14, "Shadow Rider Calyrex Alt","220/198","Alt",  "/game/pokemon-chilling-reign/shadow-rider-calyrex-vmax-220",0.0556),
    (14, "Blaziken VMAX Alt Art", "21/198",  "Alt",  "/game/pokemon-chilling-reign/blaziken-vmax-21",      0.0556),

    # ── Fusion Strike (17) ────────────────────────────────────────────
    (17, "Gengar VMAX Alt Art",   "271/264", "Alt",  "/game/pokemon-fusion-strike/gengar-vmax-271",         0.0556),
    (17, "Mew VMAX Alt Art",      "269/264", "Alt",  "/game/pokemon-fusion-strike/mew-vmax-269",            0.0556),
    (17, "Espeon VMAX Alt Art",   "270/264", "Alt",  "/game/pokemon-fusion-strike/espeon-vmax-270",         0.0556),

    # ── Battle Styles (56) ────────────────────────────────────────────
    (56, "Urshifu VMAX Alt Art",  "168/163", "Alt",  "/game/pokemon-battle-styles/urshifu-vmax-168",        0.0556),
    (56, "RS Urshifu VMAX Alt",   "169/163", "Alt",  "/game/pokemon-battle-styles/rapid-strike-urshifu-vmax-169",0.0556),
    (56, "Empoleon V Alt Art",    "145/163", "Alt",  "/game/pokemon-battle-styles/empoleon-v-145",          0.0556),

    # ── S&V Base Set (23) ─────────────────────────────────────────────
    (23, "Miraidon ex SAR",       "91/91",   "SAR",  "/game/pokemon-scarlet-violet/miraidon-ex-91",         0.1250),
    (23, "Koraidon ex SAR",       "90/91",   "SAR",  "/game/pokemon-scarlet-violet/koraidon-ex-90",         0.1250),
    (23, "Arcanine ex SAR",       "89/91",   "SAR",  "/game/pokemon-scarlet-violet/arcanine-ex-89",         0.1250),
]

inserted = skipped = 0
for (set_id, card_name, card_number, rarity, pc_path, pull_rate) in CARDS:
    try:
        cur.execute("""
            INSERT INTO chase_cards (set_id, card_name, card_number, rarity, pc_path, pull_rate_per_box)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (set_id, card_name, card_number, rarity, pc_path, pull_rate))
        inserted += 1
    except Exception as e:
        print(f'  SKIP [{set_id}] {card_name}: {e}')
        pg.rollback()
        skipped += 1
        continue
    pg.commit()

cur.execute("SELECT COUNT(*) FROM chase_cards")
total = cur.fetchone()[0]
print(f'Done. Inserted: {inserted} | Skipped: {skipped} | Total: {total}')
cur.close(); pg.close()
