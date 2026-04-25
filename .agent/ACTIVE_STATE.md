# TCGInvest — Active Sprint State
# This file is the handoff document between Strategic and Implementation phases.
# Updated at the end of every Strategic planning session.
# Last updated: 2026-04-24

---

## Sprint 5 — Execution Plan
# Status: APPROVED — Implementation phase open
# Strategic decisions locked. Open a new chat for Track A implementation.

### Architecture Decision (locked)
- A3 CardMavin: Implement as a real API fallback in first_run_v3.py.
  price_source column in monthly_snapshots ('tcgcsv' | 'cardmavin') is the tracking mechanism.
  Cron chain risk noted: score_sets.py and generate_blog_posts.py depend on first_run_v3.py — test carefully.

---

### Track A — Logic / Backend (8 tasks) ✅ COMPLETE — 2026-04-23

**A1 — Fix homepage movers blur for premium users**
- File: frontend/app/page.tsx → DailyMoversStrip component
- Bug: blur classes hardcoded — no auth check at all
- Fix: pass isPremium prop from server component; conditionally remove blur/opacity on risers+fallers panels
- API: /api/movers/daily unchanged (unauthed by design)
- Schema: no change

**A2 — BB Tracker: 7D and 30D average showing "–"**
- Endpoint: /api/sets/{set_id}/momentum (find_closest ±5 days logic exists)
- Root cause: likely tcgcsv_bb_product_id is NULL for affected sets
- Fix: diagnostic query on sets table first; improve frontend null display to distinguish "no data" vs error
- Schema: no change | Cron reads: tcgcsv_daily.py output

**A3 — BB Tracker: Verify TCGCSV price ingestion + CardMavin fallback**
- File: workspace/first_run_v3.py
- Decision: implement CardMavin API as real secondary source when TCGCSV market_price returns NULL
- Write price_source = 'cardmavin' to monthly_snapshots (column already exists)
- CRON RISK: score_sets.py (Mon 09:30) and generate_blog_posts.py (1st 10:00) depend on first_run_v3.py
- Schema: no change

**A4 — BB Tracker: Price history incomplete for some sets/ETBs**
- Endpoints: /api/sets/{set_name}/history (monthly_snapshots) + /api/etbs/{etb_id}/history (etb_price_snapshots)
- Root cause: sets joined post-launch, no backfill
- Fix: audit which set_ids have <3 monthly_snapshot rows; improve frontend sparse history handling
- Schema: no change

**A5 — BB Tracker: AI Score visible without login (gate as premium)**
- decision_score returned in /api/sets response (public, API key only)
- isPremiumUser flag exists in tracker page but not wired to AI Score column
- Fix: blur/gate decision_score display same as heat score — blurred value + premium CTA for free/unauthed
- Schema: no change

**A6 — ETB Tracker: Use tcgcsv_prices as primary, etb_price_snapshots as fallback**
- etbs.tcgcsv_product_id maps to tcgcsv_prices.product_id — plumbing exists, unused
- Fix: join tcgcsv_prices on etbs.tcgcsv_product_id for current price; fallback to etb_price_snapshots.ebay_avg_sold_gbp if NULL
- SCHEMA GUARD: do NOT create new tables — map to existing tcgcsv_prices
- Cron reads: tcgcsv_daily.py + ETB pipeline

**A7 — ROI Tracker: Set search returns no results (e.g. "Evolving Skies")**
- UI is a dropdown <select>, not text search
- Root cause: tcgcsv_bb_product_id likely NULL for popular sets
- Fix: diagnostic query on sets table for affected rows; populate missing tcgcsv_bb_product_id values; consider text filter on dropdown
- Schema: no change

**A8 — ETB Tracker: Heat map (same as BB tracker)**
- set_heat_scores keyed by set_id; ETBs linked via etbs.set_id
- Fix: join set_heat_scores on etbs.set_id in ETB API response
- Schema: no change | Cron reads: score_heat.py (daily 22:00)

---


---

## Track A — Completion Notes (2026-04-23)

### Status per task
| Task | Status | Notes |
|------|--------|-------|
| A1 | ✅ Done | `getUser()` added to homepage parallel fetch; `isPremium` prop threaded into `DailyMoversStrip`; fallers unblurred for premium |
| A2 | ✅ Done | Populated `tcgcsv_bb_product_id` for 7 sets (151, Paldean Fates, Prismatic Evolutions, Destined Rivals, White Flare, Black Bolt, Ascended Heroes). 6 sets confirmed ETB/promo-only — NULL is correct. |
| A3 | ✅ Done | `fetch_tcgcsv_bb_price()` added to `first_run_v3.py`; falls back to `tcgcsv_prices` via `tcgcsv_bb_product_id` when Dawnglare misses; writes `price_source='tcgcsv'`; cron-safe (read-only). Note: CardMavin has no JSON API — TCGCSV is the correct fallback. |
| A4 | ✅ Done | History endpoint returns `sparse: true` + `snapshot_count` when <3 snapshots. SetPageClient shows amber "Limited data" badge. Only 3 sets affected: Perfect Order, Mega Evolution (Enhanced), Journey Together (Enhanced). |
| A5 | ✅ Already done | `TrackerTable.tsx` already gates `decision_score` behind `isPremium` — confirmed correct, no change needed. |
| A6 | ✅ Done | `price_source: "ebay_snapshot"` added to all ETB API responses. Note: all 27 ETBs have `tcgcsv_product_id = NULL` — TCGCSV path is wired but inactive pending data population. |
| A7 | ✅ Done | Fixed by A2 data fix — ROI dropdown now returns 38 sets (was 31). `roi_sets` endpoint queries `tcgcsv_bb_product_id IS NOT NULL` which is now correctly populated. No code change needed. |
| A8 | ✅ Done | `set_heat_scores` LATERAL join added to both ETB query paths (default + dated snapshot). `heat_score`, `bb_trend_score`, `chase_trend_score`, `pull_rate_score` now returned in ETB API response. |

### Lessons Learned

**L1 — CardMavin has no JSON API.** Sprint plan said "CardMavin API" but cardmavin.com is a WordPress blog fronting mavin.io (eBay price aggregator). No machine-readable endpoint exists. The correct fallback is TCGCSV itself, which we already have product IDs for. Decision recorded in LOGIC_REGISTRY as PIPE-005.

**L2 — `tcgcsv_bb_product_id` was NULL for 13 sets, not because of missing data but unmapped products.** Sets like 151, Prismatic Evolutions use "Booster Bundle Display" (not "Booster Box") on TCGPlayer — required name-aware lookup. 6 sets (Hidden Fates, Champions Path, Shining Fates, Celebrations, Crown Zenith, Ascended Heroes older sets) have NO booster box product on TCGPlayer at all — ETB/promo-only. NULL is semantically correct for these.

**L3 — Frontend was not under PM2** contrary to the handoff notes. Two next-server processes running simultaneously (port 3000 owned by root, port 3001 owned by jaytee). Nginx proxies to 3000. PM2 session was lost at some point. Should set up a proper systemd unit for the frontend to prevent this happening again.

**L4 — `npm exec next start -p 3000` shell quoting issue.** The `&&`-chain causes `-p 3000` to be parsed as arguments to `npm exec` if the preceding command exits non-zero. Pattern to use: `npm exec next start -- -p 3000` (double-dash separator).

**L5 — A5 was already done.** TrackerTable.tsx had correct isPremium gating from a prior sprint. No rework needed — pre-audit before implementing saves tokens and risk.

---
### Track B — Frontend / UI (4 tasks) ✅ COMPLETE — 2026-04-23

**B1 — BB Tracker: Date snapshot picker — trim + access-gate older months**
- Bug + feature: all historical run_dates render as overflowing inline buttons
- Fix: show only current month unlocked; prior dates gated (sign-in for free, always on for premium)
- UI: compact dropdown or constrained scrollable list
- API: /api/sets/run-dates unchanged
- Schema: no change

**B2 — ETB Tracker: Month snapshot label format**
- Change "20 Apr '26" → "Apr 2026"
- Fix: toLocaleDateString('en-GB', {month:'short', year:'numeric'})
- Schema: no change | 1-line frontend fix

**B3 — BB Tracker: UI polish (text overlap, star+tick, yellow shading)**
- (1) Set name text overlapping BB price column — fix column widths/truncation
- (2) Watchlist star and green tick should be visible simultaneously — currently mutually exclusive
- (3) Yellow watchlist row shading: increase brightness to match green tick shading intensity
- Schema: no change | CSS/layout only

**B4 — BB Tracker: Date picker auth gate (companion to B1)**
- Unauthenticated: disable all options except latest run_date; tooltip "Sign in free to access historical months"
- Free user: same gate
- Premium: all dates unlocked
- Schema: no change

---

---

## Track B — Completion Notes (2026-04-23)

### Status per task
| Task | Status | Notes |
|------|--------|-------|
| B1 | ✅ Done | Date picker button strip replaced with compact `<select>` dropdown. New component: `components/tracker/DatePickerDropdown.tsx` (`'use client'`). No overflow at any viewport width. |
| B2 | ✅ Done | `fmtDate()` in `etb-tracker/page.tsx` updated — 1-line fix. `"20 Apr '26"` → `"Apr 2026"` confirmed in rendered HTML. |
| B3a | ✅ Done | Set name `Link`: `truncate max-w-[180px]` + `title` tooltip. BB price `<td>`: `whitespace-nowrap`. Inner div: `min-w-0 overflow-hidden`. Desktop table only (mobile card layout was not affected). |
| B3b | ✅ Done | Star: always `text-yellow-400` when `isStarred` — was grayed (`slate-500`) when `isBought`. Tick: `text-emerald-500/60` when starred-not-bought — was near-invisible `slate-500`. Both desktop + mobile. |
| B3c | ✅ Done | Desktop row: `bg-yellow-500/5 → /10`. Mobile card: `border-yellow-500/20 → /30`. Noticeably more visible without being garish. |
| B4 | ✅ Done | Auth gate wired into `DatePickerDropdown`: unauthed/free → historical `<option>` elements `disabled` + 🔒 prefix + contextual hint link beneath select. Premium → all dates enabled, no hint. |

### Lessons Learned

**L6 — Frontend process management pattern is still broken.** The root-owned `next-server` on port 3000 pattern (L3 from Track A) recurred: killed old process, restarted via `nohup sudo -u jaytee npm exec next start -- -p 3000`, resulting process still root-owned. Site serves correctly but this is fragile. Priority for a future session: create `tcginvest-frontend.service` systemd unit. Recorded as FE-004 in LOGIC_REGISTRY.

**L7 — Pre-read source before writing fixes.** B3b: the spec said "star and tick visible simultaneously" which sounds like a presence bug. Pre-reading `TrackerTable.tsx` revealed `showCheck = isStarred || isBought` — tick WAS present when starred, just invisible (`text-slate-500` on dark bg). The real fix was colour, not conditionals. Would have written wrong code without the read.

**L8 — `<option disabled>` is the correct auth-gate pattern for dropdowns.** Considered optgroup + separate UI labels, but native `disabled` on `<option>` is universally supported, renders a greyed-out item in all browsers, and requires zero JS. Combined with a contextual hint link below the select, this gives clear UX without custom components.

### Files changed (Track B)
- `frontend/app/tools/tracker/page.tsx` — import `DatePickerDropdown`, replace button strip
- `frontend/app/tools/etb-tracker/page.tsx` — `fmtDate()` 1-line fix
- `frontend/components/tracker/TrackerTable.tsx` — B3a/b/c polish (column, star/tick, shading)
- `frontend/components/tracker/DatePickerDropdown.tsx` — NEW client component

### Track C — Automations / Content Strategy (2 tasks) ✅ COMPLETE — 2026-04-24

**C1 — Blog content scale-up — SEO system design**
- Current: generate_blog_posts.py runs monthly (1st 10:00), depends on first_run_v3.py
- Proposed: weekly cadence — decouple from monthly run, read monthly_snapshots directly
- Candidate: activate n8n workflow "TCGInvest Weekly Blog Post Generator" (currently inactive, id: tcginvest-blog-weekly)
- blog_posts table already exists (slug, title, category, content_md, published)
- Schema: no change

**C2 — Blog SEO pillars (content strategy, no code)**
- ① Set investment guides — "Is [Set Name] worth buying in 2026?" (long-tail, high intent, one per set)
- ② Price trend reports — "Pokémon TCG prices rising/falling this month" (monthly freshness signal)
- ③ Chase card deep-dives — pull rates, PSA premium, grading ROI per card
- ④ Sealed vs singles comparison — "Should you buy sealed or singles for [Set]?"
- ⑤ Era/rotation guides — "Best Scarlet & Violet sets to invest in 2026"

---

## Track C — Completion Notes (2026-04-24)

### Status per task
| Task | Status | Notes |
|------|--------|-------|
| C1 | ✅ Done | `generate_blog_posts.py` fully decoupled from `first_run_v3.py` — reads `monthly_snapshots`, `scores`, `chase_card_prices`, `sets` directly via psycopg2. Weekly cron slot: Thu 11:00 (`0 11 * * 4`). Decision: stay on hetzner cron (not n8n) — closer to data, no Tailscale hop, existing infrastructure is clean. |
| C2 | ✅ Done | All 5 SEO pillars implemented as distinct generator functions. Each writes to `blog_posts` via slug-based upsert. Weekly runner uses skip-if-exists logic (smart incremental). CLI flags support targeted per-pillar regeneration. |

### Pillar Implementation Summary
| Pillar | Function | Slug Pattern | Category | Cadence |
|--------|----------|-------------|----------|---------|
| Set investment guides | `generate_set_investment_guide()` | `is-{set-slug}-worth-buying-2026` | guide | Once, skip-if-exists |
| Monthly price trend reports | `generate_price_trend_report()` | `pokemon-tcg-price-trends-{month-year}` | analysis | Weekly (new slug per month) |
| Chase card deep-dives | `generate_chase_card_deepdive()` | `chase-card-{card-slug}-investment-guide` | analysis | Once, skip-if-exists |
| Sealed vs singles | `generate_sealed_vs_singles()` | `sealed-vs-singles-{set-slug}` | analysis | Once, skip-if-exists |
| Era/rotation guides | `generate_era_rotation_guide()` | `best-{era-slug}-sets-to-invest-2026` | guide | Once, skip-if-exists |

### Steady-state output
- **2 new posts every Thursday** (movers + price trend, fresh slug per month)
- **Existing posts refreshed** in-place if `--all-sets` / `--all-eras` / `--all-cards` flags used
- Legacy TSX movers component still written for backward-compatible `/blog/[slug]` routing

### Lessons Learned

**L9 — Movers and price trend posts accumulate by month, not overwrite.** Both use `{month-year}` in their slug, so each monthly run creates a new URL. This is intentional — it builds an SEO archive of historical reports. The upsert still applies within the same month (Thu runs refresh the same slug until month rolls over).

**L10 — n8n workflow (tcginvest-blog-weekly) left inactive.** Decision: hetzner cron is the correct home for this pipeline. Blog generation reads live DB data, and running it on hetzner avoids a Tailscale hop + n8n overhead for a straightforward Python script. The n8n workflow exists as a backup but should not be activated unless the hetzner cron approach fails.

**L11 — Skip-if-exists logic is essential for set/era/chase guides.** With 44+ sets, 5+ eras, and 20+ chase cards, re-generating everything weekly would produce hundreds of DB writes and a slow run. The weekly runner only generates missing posts; forced regen requires explicit CLI flags. This keeps Thursday runs fast (2 posts + any newly added sets/cards).

---
### Schema Guard Summary
- Zero new tables across all 14 tasks
- All price data maps to: tcgcsv_prices, monthly_snapshots, etb_price_snapshots
- Three watchlist tables remain split by design (rule_4 — intentional)
- CardMavin fallback writes to existing price_source column in monthly_snapshots
- CRON RISK: A3 edits first_run_v3.py — score_sets.py + generate_blog_posts.py depend on it

---

## Blocked / Decisions Needed
- None — all decisions locked before handoff

---

## Architecture Decisions Pending
- Should price movers be cached (e.g. in set_heat_scores) or computed on-demand?
  - Lean: compute on-demand for now (tcgcsv_prices is indexed on snapshot_date + product_id)
  - Revisit if query time exceeds 500ms

---

## Multi-Agent Handoff Protocol
When this Strategic phase closes:
1. Update this file with final decisions ✓ (done)
2. Start a NEW chat for the Implementation phase
3. Paste ACTIVE_STATE.md into the new chat as first context
4. Reference MANIFEST.json for all DB table decisions
