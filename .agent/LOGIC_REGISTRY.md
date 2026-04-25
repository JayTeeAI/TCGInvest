# TCGInvest — Architectural Logic Registry
# Purpose: Record the "Why" behind every major design decision.
# Update this file whenever a structural choice is made. Never delete entries — mark as SUPERSEDED if changed.
# Last updated: 2026-04-23

---

## Database Architecture

### [ARCH-001] tcgcsv_prices is the single price source of truth
**Decision:** All daily price data from TCGCSV flows into one table: `tcgcsv_prices`.
**Why:** At 11.4M rows / 2.4 GB, duplicating this data would be catastrophic. The table uses
`product_id` + `group_id` + `snapshot_date` as the natural key and `sub_type_name` to discriminate
product variants (Holofoil, Normal, etc.). Any new price source should either add rows here or
be bridged via a separate snapshot table (see ARCH-002 for exceptions).
**Cron dependency:** `workspace/tcgcsv_daily.py` (daily 21:00) is the sole writer.

### [ARCH-002] Separate snapshot tables for non-TCGCSV sources
**Decision:** ETB prices live in `etb_price_snapshots`, chase card prices in `chase_card_prices`.
**Why:** ETB prices come from eBay Finding API (different schema — includes `sealed_premium_pct`,
PSA10 promo data). Chase prices come from PriceCharting scrape (includes `psa10_gbp`). These fields
have no analogue in `tcgcsv_prices`. Forcing them in would require nullable columns that destroy
query semantics.
**Cron dependency:** `etb/run_etb_pipeline.py` (Sun 08:00) and `chase/fetch_prices_scrape.py` (daily 06:00).

### [ARCH-003] Three watchlist tables by product domain
**Decision:** `watchlist` (BB/sets), `etb_watchlist`, `chase_watchlist` are separate tables.
**Why:** Each product type has different FK targets (sets.id, etbs.id, chase_cards.id) and different
digest behaviours. A single polymorphic watchlist table with nullable FKs would complicate joins
and digest queries. This split is intentional — do NOT merge.
**Cron dependency:** `workspace/send_digest.py` reads all three.

### [ARCH-004] monthly_snapshots stores run_date as TEXT
**Decision:** `monthly_snapshots.run_date` is TEXT (e.g. "2026-04-01"), not DATE.
**Why:** Legacy from the original pipeline design. Changing to DATE requires a migration and a
rewrite of all queries that do string comparison on run_date. Flag for future cleanup but do not
change without a full migration plan.
**Risk:** String sorting works correctly as long as format stays YYYY-MM-DD.

### [ARCH-005] sets.tcgcsv_group_ids is an ARRAY column
**Decision:** `sets.tcgcsv_group_ids` is a PostgreSQL ARRAY (integer[]).
**Why:** Some Pokémon sets span multiple TCGCSV group IDs (e.g. standard + reverse holo groups).
Using an array avoids a join table for a one-to-few relationship.
**Usage:** `tcgcsv_daily.py` expands this array to fetch prices for all groups per set.

### [ARCH-006] page_events uses JSONB metadata column
**Decision:** `page_events.metadata` is JSONB.
**Why:** Analytics event payloads are heterogeneous — a tracker view has different fields than a
premium CTA click. JSONB avoids table-per-event-type sprawl while remaining queryable.

### [ARCH-007] portfolio_items uses soft delete (deleted_at)
**Decision:** Portfolio rows are never hard-deleted; `deleted_at` timestamp is set instead.
**Why:** Users may want to undo. Also preserves historical P&L calculation integrity.

---

## Pipeline Architecture

### [PIPE-001] BB pipeline must run before AI scoring (Monday sequencing)
**Decision:** `first_run_v3.py` at 09:00, `score_sets.py` at 09:30, `generate_blog_posts.py` at 10:00.
**Why:** AI scoring reads the latest `monthly_snapshots` and `sets` data written by `first_run_v3.py`.
Blog generator reads the latest `scores`. The 30-minute gaps are safety buffers.
**Risk:** If `first_run_v3.py` runs long, `score_sets.py` may read stale data. Monitor `run_log`.

### [PIPE-002] Chase scraper runs at 06:00 to avoid PriceCharting rate limits
**Decision:** `chase/fetch_prices_scrape.py` runs at 06:00 UTC.
**Why:** PriceCharting shows higher traffic 08:00–22:00 UK time. Early morning reduces scrape
failure rate. No historical backfill is possible — data only exists from Apr 2026 forward.

### [PIPE-003] Heat scores calculated at 22:00 (after TCGCSV ingestion)
**Decision:** `score_heat.py` runs at 22:00, one hour after `tcgcsv_daily.py` (21:00).
**Why:** Heat scores are derived from `tcgcsv_prices` momentum. Must run after daily ingestion.

### [PIPE-004] send_digest.py gates internally by user frequency setting
**Decision:** Digest cron runs daily at 09:15 but the script only sends to users whose
`digest_frequency` setting (`users.digest_frequency`) matches the current day.
**Why:** Avoids multiple cron entries. The script handles weekly/monthly/daily logic internally.
**Dependency:** Reads `watchlist`, `etb_watchlist`, `chase_watchlist`, writes `digest_log`.

---

## Frontend Architecture

### [FE-001] sitemap.ts is pre-rendered at build time
**Decision:** `sitemap.ts` generates the sitemap statically during `npm run build`.
**Why:** Next.js App Router pre-renders metadata exports. Any sitemap change requires TWO builds:
first to write the file, second to capture it.
**Rule:** After editing sitemap.ts, always run `npm run build` twice before deploying.

### [FE-002] JSON-LD schema only in server components
**Decision:** All JSON-LD structured data is rendered in server components, never client components.
**Why:** Google's crawler requires JSON-LD in the initial HTML response. Client components render
after hydration and may be missed.

### [FE-003] API keys never in browser bundle
**Decision:** All third-party API keys (TCGCSV, PriceCharting, Groq) are proxied server-side only.
**Why:** ADR-009. Browser bundle is publicly inspectable. FastAPI is the sole API consumer.

### [FE-005] Date picker uses native <select> with disabled options for auth gating
**Decision:** The BB Tracker and ETB Tracker date pickers use a single `<select>` element.
Historical `<option>` elements are set `disabled` for unauthed and free users.
A contextual hint link sits below the select pointing to sign-in or upgrade.
**Why:** A button strip overflows on narrow viewports once more than ~4 months of data exist.
Native `disabled` on `<option>` is universally supported without custom JS, renders greyed-out
in all browsers, and preserves the option text (users can see what they're missing).
The hint link provides the upgrade/sign-in path without hiding the data's existence.
**Auth logic:** `isPremiumUser` (role === 'premium' || 'admin') → all dates enabled.
Free or unauthed → only `runDates[0]` (latest) is selectable.
**Component:** `components/tracker/DatePickerDropdown.tsx` (`'use client'` — needs useRouter).
**Added:** 2026-04-23 Sprint 5 Track B.

---

## Infrastructure

### [INFRA-001] Admin dashboard is Tailscale-only
**Decision:** The ops dashboard on paperclip:8888 is only accessible over Tailscale.
**Why:** ADR-010. Exposes prod Postgres read-only over Tailscale. Zero public attack surface.

### [INFRA-002] All main-branch deploys require Discord approval
**Decision:** GitHub Actions workflow gates on Discord human-in-the-loop approval before touching prod.
**Why:** ADR-015. Prevents accidental deploys. The staging branch deploys to paperclip automatically.

### [INFRA-003] CLAUDE.md is synced to paperclip every 6 hours
**Decision:** `sync-brain.sh` on paperclip cron copies CLAUDE.md from hetzner.
**Why:** n8n agents on paperclip read CLAUDE.md for project context. Keeps both servers in sync.

### [PIPE-005] TCGCSV is the fallback price source for Dawnglare misses (not CardMavin)
**Decision:** When `first_run_v3.py` cannot find a booster box price on Dawnglare, it falls back
to querying `tcgcsv_prices` via `sets.tcgcsv_bb_product_id`. Writes `price_source = 'tcgcsv'`
to `monthly_snapshots`.
**Why:** CardMavin has no machine-readable JSON API (it is a WordPress blog). TCGCSV already
contains sealed product prices (booster box, booster bundle display) and we have the product IDs
mapped. This is cleaner, faster, and consistent with the existing architecture.
**Cron safety:** The fallback is a read-only DB query. It does not affect the `score_sets.py`
or `generate_blog_posts.py` downstream chain — both read `monthly_snapshots` by `set_id`, not
`price_source`.
**Added:** 2026-04-23 Sprint 5 Track A.

### [PIPE-006] Some sets have no booster box on TCGPlayer — NULL tcgcsv_bb_product_id is correct
**Decision:** Hidden Fates, Champions Path, Shining Fates, Celebrations 25th, Crown Zenith are
ETB/promo-only sets with no standard booster box product on TCGPlayer. Their
`sets.tcgcsv_bb_product_id` is intentionally NULL.
**Why:** These sets were never sold as booster boxes. Forcing a product ID mapping would produce
misleading price data. Momentum (7D/30D) correctly returns `null` for these sets; the BB Tracker
correctly shows `—`. Do NOT attempt to populate these with ETB prices as a proxy.
**Added:** 2026-04-23 Sprint 5 Track A.

### [FE-004] Frontend process runs as root on port 3000 — not under PM2
**Decision:** The Next.js frontend runs as a root-owned `next-server` process on port 3000,
started manually (or by a deploy script). PM2 is not managing it despite prior notes.
**Why it matters:** `pm2 restart all` will silently do nothing. To restart the frontend, kill
the process and re-launch with:
`sudo bash -c 'cd /root/.openclaw/frontend && nohup npm exec next start -- -p 3000 >> /root/.openclaw/logs/frontend.log 2>&1 &'`
**Recommendation:** Create a systemd unit (`tcginvest-frontend.service`) to manage this properly.
**Added:** 2026-04-23 Sprint 5 Track A.

### [ARCH-008] ETBs use eBay snapshot prices; TCGCSV path is wired but inactive
**Decision:** All 27 ETBs currently price from `etb_price_snapshots.ebay_avg_sold_gbp`. The
`etbs.tcgcsv_product_id` column exists and is referenced in API code but is NULL for all ETBs.
**Why:** Pokemon Centre ETBs are not sold on TCGPlayer USA — no TCGCSV product exists.
The API returns `price_source: "ebay_snapshot"` on all ETB rows to make this transparent.
**Do NOT** try to populate `tcgcsv_product_id` for PC ETBs without verifying product existence first.
**Added:** 2026-04-23 Sprint 5 Track A.


### [PIPE-007] Blog pipeline runs on hetzner cron, not n8n (decoupled from first_run_v3.py)
**Decision:** `generate_blog_posts.py` runs weekly on hetzner (Thu 11:00 via `/etc/cron.d/tcginvest`).
It reads `monthly_snapshots`, `scores`, `chase_card_prices`, and `sets` directly via psycopg2.
No dependency on `first_run_v3.py`. The n8n workflow `tcginvest-blog-weekly` exists on paperclip
but is intentionally inactive.
**Why:** Blog generation is a DB-read-heavy Python script. Running it on hetzner avoids a Tailscale
network hop and n8n Docker overhead. The existing cron infrastructure is well-organised and monitored.
n8n is reserved for event-driven and inter-service workflows (CI/CD, digests, alerts).
**Cron slot:** `0 11 * * 4` — Thu 11:00, well after the Monday pipeline chain (09:00–10:00).
**Added:** 2026-04-24 Sprint 5 Track C.

### [CONTENT-001] Blog SEO pillars use slug-based upsert with skip-if-exists weekly logic
**Decision:** All 5 content pillars write to `blog_posts` via `ON CONFLICT (slug) DO UPDATE`.
Set guides, sealed vs singles, era guides, and chase deepdives skip generation if a post with
that slug already exists (unless `--all-sets` / `--all-eras` / `--all-cards` flags are passed).
Movers and price trend reports use `{month-year}` slugs — new slug each calendar month, so they
accumulate as an SEO archive rather than overwriting.
**Why:** With 44+ sets, 5+ eras, and 20+ chase cards, unconditional weekly regeneration produces
hundreds of DB writes and slow cron runs for zero SEO benefit (evergreen content doesn't need
weekly refresh). Only time-sensitive posts (movers, price trend) get fresh content each run.
**Table:** `blog_posts` (existing — no new tables). Conflict key: `slug`.
**Added:** 2026-04-24 Sprint 5 Track C.

### [CONTENT-002] Legacy TSX movers component maintained for backward-compatible blog routing
**Decision:** `generate_blog_posts.py` continues to write `.tsx` component files to
`frontend/components/blog/` and updates `frontend/lib/blog/posts.ts` and the blog router
alongside the DB upsert.
**Why:** The blog `[slug]` page currently uses a component-switch pattern (pre-Sprint 5 design).
Until the blog is fully migrated to DB-driven markdown rendering, the TSX component is required
for the `/blog/[slug]` route to resolve. This is tech debt — a future sprint should migrate to
rendering `blog_posts.content_md` directly, removing the TSX generation entirely.
**Added:** 2026-04-24 Sprint 5 Track C.
