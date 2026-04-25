# TCGInvest — Project Brain
# CLAUDE.md v2.0 | Updated April 2026 | Author: Jaimish Tank
# This file lives in /root/.openclaw/CLAUDE.md (canonical source)
# It is auto-synced to Paperclip via the ops/sync-brain.sh script.
# Update it whenever you learn something new about the project.

---

## 1. What TCGInvest Is

TCGInvest (tcginvest.uk) is a SaaS investment platform for Pokemon TCG collectors and investors.
The market is full of trackers for individual cards — TCGInvest's edge is the **investment spin**:
AI-scored booster boxes, ETB grading premiums, ROI analysis, and sealed product intelligence.

The business model is freemium: free tools drive SEO traffic, Premium (£3/month via Stripe)
unlocks the analytical layer. Content is the primary acquisition channel.

**Mission:** Make TCGInvest the go-to data platform for serious Pokemon TCG investors in the UK and beyond.

---

## 2. Server Infrastructure

### Server 1 — Production (hetzner)
- SSH alias: `hetzner` (also aliased as `tcginvest`)
- IP: 95.217.15.156, Port: 2222, User: jaytee
- Identity file: ~/.ssh/hetzner_openclaw
- Hosts: tcginvest.uk (live site)
- Frontend: Next.js 16 at /root/.openclaw/frontend — PM2 process: tcginvest-frontend, port 3000
- Backend: FastAPI v3 at /root/.openclaw/api/main.py — systemd: tcginvest-api, port 8000
- Database: PostgreSQL 16 at localhost:5432, db: tcginvest, user: tcginvest
- Reverse proxy: nginx — /api/* and /auth/* → port 8000, all else → port 3000
- SSL: Let's Encrypt

### Server 2 — Preprod / Admin / n8n (paperclip)
- SSH alias: `paperclip`
- IP: 46.62.193.245, Port: 2222, User: jaytee
- Tailscale IP: 100.107.74.24
- Hosts: preprod environment, admin dashboard (port 8888, Tailscale only)
- Admin dashboard reads prod Postgres over Tailscale (100.91.252.77)
- n8n automation: http://100.107.74.24:5678 (Docker, Tailscale-only)
- Deployment bridge: GitHub `staging` branch → Paperclip, `main` branch → Hetzner

### Key file locations (prod server)
- Frontend: /root/.openclaw/frontend/
- Backend: /root/.openclaw/api/main.py
- Ops scripts: /root/.openclaw/.claude/ops/
- GitHub Actions: /root/.openclaw/.github/workflows/
- Tests: /root/.openclaw/api/tests/
- Secrets: /root/.openclaw/api/.env (chmod 600 — never modify, never read aloud)
- Frontend env: /root/.openclaw/frontend/.env.local
- nginx config: /etc/nginx/sites-enabled/default
- Monthly pipeline: /root/.openclaw/workspace/first_run_v3.py
- ETB pipeline: /root/.openclaw/etb_ebay.py
- Python venv: source /root/.openclaw/workspace/venv/bin/activate

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI v3 (Python) |
| Database | PostgreSQL 16 |
| Auth | Google OAuth 2.0 + JWT (HTTP-only cookie) |
| Payments | Stripe — £3/month (price_1TLjVTIED31jcWNjv0s8SszJ) |
| AI scoring | Groq API — llama-3.3-70b-versatile |
| Data sources | dawnglare.com (scrape), PokemonWizard.com (scrape), eBay Finding API, open.er-api.com |
| Process mgr | PM2 v6 (frontend), systemd (API) |
| Reverse proxy | nginx + Let's Encrypt |
| Hosting | Hetzner VPS (x2) |
| Admin | FastAPI dashboard on Paperclip, Tailscale-only |
| Automation | n8n on Paperclip (Docker) |
| CI/CD | GitHub Actions → n8n webhook → Discord approval → deploy |

---

## 4. Live Tools

### Booster Box Tracker (LIVE)
- Route: /tools/tracker
- Cadence: Weekly (cron, was monthly — migrated April 2026)
- Covers 44+ Pokemon TCG sets
- Free: price table. Login: history + charts. Premium: AI scores + buy/sell signals.

### Pokemon Centre ETB Tracker (MVP LIVE)
- Route: /tools/etb-tracker
- Cadence: Weekly (pending eBay API approval for full pipeline)
- Covers sealed ETB prices, raw promo values, PSA 10 premiums, grading ratios
- 27 PC ETBs seeded

### Planned Tools (pipeline)
- ROI Calculator — on demand, sealed product ROI over time
- Price Alerts — real-time threshold notifications
- Investor Dashboard — unified watchlist view across all tools

---

## 5. Subscription Tiers

| Tier | Price | Key unlock |
|---|---|---|
| Free (no login) | £0 | Basic price tables |
| Free (login) | £0 | History, charts, watchlist (5 BB / 3 ETB) |
| Premium | £3/month | AI scores, buy/sell signals, unlimited watchlist, drill-downs |

Single subscription unlocks all tools. No per-tool pricing.

---

## 6. Agent Roles

When starting a session, specify which role to work in. Each role has different priorities and constraints.

### 🔧 Developer
**Activate with:** "Act as the Developer agent"
- Builds new tools and features (Next.js components, FastAPI endpoints, DB schema)
- Fixes bugs, improves performance
- Always targets preprod first, never prod directly
- Follows deploy protocol (see Section 8)

### 📈 SEO & Content Strategist
**Activate with:** "Act as the SEO agent"
- Writes 4-pillar content calendar articles
- Updates page metadata, JSON-LD schema, sitemap, robots.txt
- Target keywords: pokemon booster box tracker, pokemon centre etb tracker, sealed pokemon investment uk

### 🧠 Product Strategist
**Activate with:** "Act as the Product Strategist agent"
- Proposes new investment tools and features for the roadmap
- Analyses the TCG market landscape and competitor gaps

### 🛡️ Ops & Security
**Activate with:** "Act as the Ops agent"
- Runs server health checks, monitors logs, manages cron jobs
- Manages Certbot renewal, backups, nginx config
- Manages n8n workflows on Paperclip

---

## 7. Deployment Protocol

**Golden rule: preprod first, always.**
**Git bridge: staging branch → Paperclip, main branch → Hetzner**

### Standard deploy sequence
```bash
# 1. Push to staging branch (triggers Paperclip deploy via GitHub Actions)
git push origin staging

# 2. After QA on preprod, push to main (triggers Discord approval workflow)
git push origin main
# n8n sends Discord Approve/Reject button — wait for human approval
# On Approve: n8n runs ops/deploy-prod.sh on Hetzner

# 3. Emergency direct deploy (skip approval — Ops role only)
bash /root/.openclaw/.claude/ops/deploy-prod.sh
```

### Key deploy rules
- Never restart PM2 without a successful build first
- Never write .tsx files with bash heredocs — use Python writes
- Always `cp file.tsx file.tsx.bak` before editing production files
- Client components with "use client" cannot export metadata — use layout.tsx wrapper
- OG images in /public/ require a build + restart to be served
- After any DB data change: `rm -rf /root/.openclaw/frontend/.next/cache` then pm2 restart

### Service management commands
```bash
sudo pm2 restart tcginvest-frontend          # Restart frontend
sudo systemctl restart tcginvest-api         # Restart API
sudo pm2 logs tcginvest-frontend --lines 30  # Frontend logs
sudo journalctl -u tcginvest-api -n 30       # API logs
sudo nginx -t && sudo systemctl reload nginx # Reload nginx
```

---

## 8. Agile Lifecycle (Autonomous)

### CI/CD Flow
```
git push any-branch
    → GitHub Actions: lint + pytest
    → POST to n8n webhook with {status, branch, commit}
    → If branch=main: n8n sends Discord approval request
    → On Approve: deploy-prod.sh runs on Hetzner
    → If branch=staging: auto-deploy to Paperclip (no approval)
```

### n8n Workflows (on Paperclip, Tailscale-only)
1. **CI Result Handler** — receives GitHub Actions webhook, routes by branch
2. **Discord Approval Gate** — sends Approve/Reject embed for main-branch merges
3. **Deploy Handler** — executes deploy scripts on approval
4. **Weekly Data Pipeline** — triggers BB and ETB scrapers (replaces cron)
5. **Health Monitor** — pings prod endpoints, alerts on failure

### Ops scripts (/root/.openclaw/.claude/ops/)
- `build-api.sh` — installs deps, validates FastAPI startup
- `build-frontend.sh` — runs next build, reports success/fail
- `test.sh` — runs pytest in venv
- `deploy-prod.sh` — full prod deploy (build → test → restart)
- `deploy-staging.sh` — deploy to Paperclip preprod
- `health-check.sh` — pings all endpoints, checks PM2/systemd status
- `sync-brain.sh` — copies CLAUDE.md to Paperclip (self-healing sync)

---

## 9. Safety Protocols

These are non-negotiable in every session regardless of role.

1. **Preprod first** — all new code goes to Server 2 (paperclip) before touching prod
2. **Never read .env files aloud** — secrets stay in /root/.openclaw/api/.env
3. **No direct DB writes** — all database changes go through the FastAPI layer or explicit migrations
4. **Backup before editing** — always cp before modifying any production file
5. **Build must succeed** — never restart PM2 on a failed build
6. **Watchlist limits enforced server-side** — free tier limits must be checked in API, not just frontend
7. **No .env modifications** — treat all .env files as read-only reference
8. **Discord approval required** — all main-branch deploys require human-in-the-loop approval

---

## 10. Outstanding Security Recommendations

- [ ] Certbot auto-renewal — verify timer is active, test dry-run before cert expiry
- [ ] Offsite backups — pg_dump needs automatic copy offsite after each run
- [ ] Reduce JWT max_age from 30 days to 7 days
- [ ] Enforce watchlist limits server-side (currently frontend only)
- [ ] Tighten CSP — remove unsafe-inline and unsafe-eval when frontend is stable
- [ ] Run OWASP ZAP scan before significant user growth

---

## 11. SEO State

- Google Search Console verified (property: https://tcginvest.uk)
- Rich results validated on Booster Box Tracker and ETB Tracker (FAQPage schema)
- sitemap.xml: 4 URLs (homepage 1.0, tracker 0.9, etb-tracker 0.9, premium 0.6)
- robots.txt: disallows /auth/callback, /api/, /premium/success

### When adding a new page
1. Add metadata export to page.tsx (server component) or a layout.tsx wrapper
2. Add JSON-LD schema in a server component (never client component)
3. Update /root/.openclaw/frontend/app/sitemap.ts
4. Rebuild and deploy
5. Request indexing in Google Search Console

---

## 12. Content Strategy (4 Pillars)

| Pillar | Focus | CTA |
|---|---|---|
| P1 — Market Intelligence | News, price spikes, rotation events | Link to tracker |
| P2 — Beginner Guides | How-to, evergreen explainers | Email capture |
| P3 — Set Deep-Dives | Per-set ROI, pull rates | Affiliate / Premium |
| P4 — Logistics & Trust | Auth, grading, platforms | Newsletter |

---

## 13. Architecture Decision Records (summary)

| ADR | Decision |
|---|---|
| ADR-003 | Google OAuth only — no passwords |
| ADR-006 | Three-tier freemium model |
| ADR-007 | PostgreSQL (migrated from SQLite) |
| ADR-008 | eBay Finding API as primary ETB price source |
| ADR-009 | API key proxied server-side only — never in browser bundle |
| ADR-010 | Admin dashboard on Paperclip via Tailscale only |
| ADR-011 | SEO metadata via Next.js App Router metadata API |
| ADR-012 | JSON-LD schema in server components only |
| ADR-013 | Content-first SEO strategy targeting sealed investment niche |
| ADR-014 | GitHub as deployment bridge (staging→Paperclip, main→Hetzner) |
| ADR-015 | All main-branch deploys require Discord human-in-the-loop approval |
| ADR-016 | n8n on Paperclip handles all automation (Tailscale-only access) |

---

## 14. Session Learnings Log

<!-- LEARNINGS START — append below this line -->

[2026-04-14] [Setup] — CLAUDE.md created. SSH aliases hetzner, tcginvest, and paperclip confirmed.

[2026-04-18] [Ops] — Autonomous Agile lifecycle initialised. Git repo init'd at /root/.openclaw.
Ops scripts created at /root/.openclaw/.claude/ops/. GitHub Actions workflow at .github/workflows/.
n8n on Paperclip confirmed running (Docker, port 5678). Existing ticket_intake.json workflow found.
CLAUDE.md v2.0 published — now tracks CI/CD, Discord approval gate, and n8n workflow inventory.
sync-brain.sh handles self-healing CLAUDE.md sync to Paperclip.

<!-- LEARNINGS END -->

---

*Last updated: 2026-04-18 | Version: 2.0*
*Update this file at the end of every session that produces new knowledge about the project.*

---

## 12. Sprint 4 — Batch 3 Complete (2026-04-21)

### Momentum UI shipped
- `lib/api.ts` — added `getSetMomentum(setId: number)` fetch function
- `TrackerTable.tsx` — 7d % / 30d % column added to desktop table and mobile card view
  - Premium users: live coloured pills (green/red) fetched client-side via `useEffect` across all sets
  - Free users: blurred placeholder + 🔒 lock icon linking to /premium
- `/sets/[slug]/page.tsx` — momentum pills rendered server-side below the 4-stat price card grid
  - BB 7d, BB 30d, ETB 7d, ETB 30d pills with ▲/▼ indicators and colour coding
  - Uses `set.id` (integer) for the momentum API call — not set name
  - Null-safe: only renders if at least one value is non-null

### Bug fixes
- `/api/sets/{set_id}/momentum` route was shadowed by `/api/sets/{set_name}/history` (FastAPI first-match routing)
  — fixed by moving momentum route to line 155 (between `run-dates` and `{set_name}/history`)
- `_RDC` (RealDictCursor) was not defined at module scope in main.py
  — fixed by adding `from psycopg2.extras import RealDictCursor as _RDC` inside the momentum endpoint

### Price history clarification
- All 46 sets have `monthly_snapshots` data (BB prices) — backfill is complete and working
- Chase card `chase_card_prices` only has 3 days of data (Apr 19–21): PriceCharting API is live-only,
  no historical backfill possible — history accumulates weekly going forward
- Momentum endpoint reads from `tcgcsv_prices` (11.4M rows, Feb 2024–Apr 2026) — data is healthy

---

## 15. Schema Guard & Persistent Environment Memory
*Added: 2026-04-23 — Initialized by Claude Systems Architect Protocol*

The `.agent/` directory at `/root/.openclaw/.agent/` is the **Persistent Environment Memory** layer.
It contains the living Source of Truth for the entire system. Every agent and every session MUST
consult these files before making structural changes.

### Files

| File | Purpose |
|---|---|
| `.agent/MANIFEST.json` | Live snapshot: all DB tables + schemas, cron jobs, n8n workflows, route map |
| `.agent/LOGIC_REGISTRY.md` | Architectural "Whys" — the reasoning behind every structural decision |
| `.agent/ACTIVE_STATE.md` | Current sprint status and multi-agent handoff doc |
| `.agent/refresh.sh` | Run to update MANIFEST.json with latest DB sizes and cron state |

---

## 16. Hard Guardrails — Non-Negotiable in Every Session

### GUARDRAIL-1: Mapping First Rule
**NEVER suggest a new database table without first reading `.agent/MANIFEST.json`.**
There are 19 tables. Before adding any new table:
1. Open MANIFEST.json and review all 19 tables
2. Identify whether the new data can map to an existing table
3. If yes — map it. If genuinely no fit — document the decision in LOGIC_REGISTRY.md with an ARCH-XXX entry.
4. Special warning: `tcgcsv_prices` (2.4 GB) is the single source of truth for all raw price history.
   Do NOT create parallel price tables.

### GUARDRAIL-2: Cron Safety Rule
**Before editing ANY pipeline script, check MANIFEST.json `cron_jobs` for dependents.**
Critical dependency chain (Monday pipeline):
```
first_run_v3.py (09:00) → score_sets.py (09:30) → generate_blog_posts.py (10:00)
```
Daily chain:
```
tcgcsv_daily.py (21:00) → score_heat.py (22:00)
chase/fetch_prices_scrape.py (06:00) [independent]
check_alerts.py + send_digest.py (09:15) [reads from multiple tables]
```
If editing a script that any downstream job reads from, the downstream job must be tested too.

### GUARDRAIL-3: Multi-Agent Handoff Protocol
**At the end of every Strategic planning phase:**
1. Update `.agent/ACTIVE_STATE.md` with all decisions made
2. Summarise the implementation plan clearly in ACTIVE_STATE.md
3. **Instruct Jaytee to start a NEW chat** for the Implementation phase
4. The new chat should begin by reading ACTIVE_STATE.md and MANIFEST.json
This preserves context window efficiency and prevents strategic drift during implementation.

### GUARDRAIL-4: Schema Change Pattern
When any DDL is required (ALTER TABLE, CREATE TABLE, DROP):
1. Always `cp` the affected migration script before editing
2. Test on paperclip (preprod) first
3. Use the pattern: `PGPASSWORD='...' psql -h 127.0.0.1 -U tcginvest -d tcginvest -c '...'`
4. Update MANIFEST.json after migration (run `.agent/refresh.sh`)

### GUARDRAIL-5: The .env Contract
`/root/.openclaw/api/.env` is **read-only**. Never modify it. Never print its contents to a
terminal that persists in logs. When credentials are needed, grep for the specific key only.


---

## Sprint 5 Track B — Session log (2026-04-23)

### Completed tasks
| Task | Status | Notes |
|------|--------|-------|
| B1 | ✅ Done | Date picker button strip replaced with `<select>` dropdown (`DatePickerDropdown.tsx` — new component). Compact, no overflow. |
| B2 | ✅ Done | ETB `fmtDate()` updated: `"20 Apr '26"` → `"Apr 2026"`. 1-line change in `etb-tracker/page.tsx`. |
| B3a | ✅ Done | Set name column: `truncate max-w-[180px] title={set.name}` on Link; BB price td: `whitespace-nowrap`. Both desktop + mobile. |
| B3b | ✅ Done | Star always yellow when `isStarred` (was grayed when bought). Tick always `text-emerald-500/60` when starred-not-bought (was invisible `slate-500`). Both desktop + mobile. |
| B3c | ✅ Done | Yellow row shading: `bg-yellow-500/5` → `bg-yellow-500/10` desktop; `border-yellow-500/20` → `border-yellow-500/30` mobile. |
| B4 | ✅ Done | Auth gate wired into `DatePickerDropdown`: unauthed/free = historical options `disabled` + 🔒 prefix + hint link below select; premium = all dates enabled. |

### Files changed
- `frontend/app/tools/tracker/page.tsx` — import + replaced button strip with `<DatePickerDropdown />`
- `frontend/app/tools/etb-tracker/page.tsx` — `fmtDate()` 1-line fix
- `frontend/components/tracker/TrackerTable.tsx` — B3a/b/c polish
- `frontend/components/tracker/DatePickerDropdown.tsx` — NEW: `'use client'` dropdown component

### Lessons Learned
- **L6 — Port 3000 root process pattern repeats.** After killing root's next-server and restarting via `nohup sudo -u jaytee npm exec next start -- -p 3000`, the process still shows as root owner but serves correctly. The EADDRINUSE noise in the log is from the stale port-3001 process (285403, jaytee, Apr13) still running — harmless but should be cleaned up. Consider setting up a systemd unit for the frontend to prevent this recurring (L3 carryover).
- **L7 — `showCheck` tick was always visible when starred** — the real B3b bug was the tick *colour* (`slate-500` = near-invisible on dark bg) not its *presence*. Pre-reading the source caught this before writing wrong code.
