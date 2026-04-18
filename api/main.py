#!/usr/bin/env python3
"""
TCG Invest — FastAPI layer v3
Migrated: SQLite -> Postgres
Added: ETB tracker endpoints
"""

import os
import psycopg2
import psycopg2.extras
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv
import hashlib
import secrets
import httpx
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

load_dotenv()

# Set image mapping from Pokemon TCG API (logo URLs)
SET_IMAGE_MAP = {"151": {"id": "sv3pt5", "logo": "https://images.pokemontcg.io/sv3pt5/logo.png", "symbol": "https://images.pokemontcg.io/sv3pt5/symbol.png"}, "Ascended Hereos": {"id": "me2pt5", "logo": "https://images.scrydex.com/pokemon/me2pt5-logo/logo", "symbol": ""}, "Astral Radiance": {"id": "swsh10", "logo": "https://images.pokemontcg.io/swsh10/logo.png", "symbol": "https://images.pokemontcg.io/swsh10/symbol.png"}, "Battle Styles": {"id": "swsh5", "logo": "https://images.pokemontcg.io/swsh5/logo.png", "symbol": "https://images.pokemontcg.io/swsh5/symbol.png"}, "Black Bolt": {"id": "zsv10pt5", "logo": "https://images.pokemontcg.io/zsv10pt5/logo.png", "symbol": "https://images.pokemontcg.io/zsv10pt5/symbol.png"}, "Brilliant Stars": {"id": "swsh9", "logo": "https://images.pokemontcg.io/swsh9/logo.png", "symbol": "https://images.pokemontcg.io/swsh9/symbol.png"}, "Celebrations 25th": {"id": "cel25", "logo": "https://images.pokemontcg.io/cel25/logo.png", "symbol": "https://images.pokemontcg.io/cel25/symbol.png"}, "Champions Path": {"id": "swsh35", "logo": "https://images.pokemontcg.io/swsh35/logo.png", "symbol": "https://images.pokemontcg.io/swsh35/symbol.png"}, "Chilling Reign": {"id": "swsh6", "logo": "https://images.pokemontcg.io/swsh6/logo.png", "symbol": "https://images.pokemontcg.io/swsh6/symbol.png"}, "Cosmic Eclipse": {"id": "sm12", "logo": "https://images.pokemontcg.io/sm12/logo.png", "symbol": "https://images.pokemontcg.io/sm12/symbol.png"}, "Crown Zenith": {"id": "swsh12pt5", "logo": "https://images.pokemontcg.io/swsh12pt5/logo.png", "symbol": "https://images.pokemontcg.io/swsh12pt5/symbol.png"}, "Darkness Ablaze": {"id": "swsh3", "logo": "https://images.pokemontcg.io/swsh3/logo.png", "symbol": "https://images.pokemontcg.io/swsh3/symbol.png"}, "Destined Rivals": {"id": "sv10", "logo": "https://images.pokemontcg.io/sv10/logo.png", "symbol": "https://images.pokemontcg.io/sv10/symbol.png"}, "Evolutions": {"id": "xy12", "logo": "https://images.pokemontcg.io/xy12/logo.png", "symbol": "https://images.pokemontcg.io/xy12/symbol.png"}, "Evolving Skies": {"id": "swsh7", "logo": "https://images.pokemontcg.io/swsh7/logo.png", "symbol": "https://images.pokemontcg.io/swsh7/symbol.png"}, "Fusion Strike": {"id": "swsh8", "logo": "https://images.pokemontcg.io/swsh8/logo.png", "symbol": "https://images.pokemontcg.io/swsh8/symbol.png"}, "Hidden Fates": {"id": "sm115", "logo": "https://images.pokemontcg.io/sm115/logo.png", "symbol": "https://images.pokemontcg.io/sm115/symbol.png"}, "Journey Together": {"id": "sv9", "logo": "https://images.pokemontcg.io/sv9/logo.png", "symbol": "https://images.pokemontcg.io/sv9/symbol.png"}, "Journey Together (Enhanced)": {"id": "sv9", "logo": "https://images.pokemontcg.io/sv9/logo.png", "symbol": "https://images.pokemontcg.io/sv9/symbol.png"}, "Lost Origin": {"id": "swsh11", "logo": "https://images.pokemontcg.io/swsh11/logo.png", "symbol": "https://images.pokemontcg.io/swsh11/symbol.png"}, "Lost Thunder": {"id": "sm8", "logo": "https://images.pokemontcg.io/sm8/logo.png", "symbol": "https://images.pokemontcg.io/sm8/symbol.png"}, "Mega Evolution": {"id": "me1", "logo": "https://images.pokemontcg.io/me1/logo.png", "symbol": "https://images.pokemontcg.io/me1/symbol.png"}, "Mega Evolution (Enhanced)": {"id": "me1", "logo": "https://images.pokemontcg.io/me1/logo.png", "symbol": "https://images.pokemontcg.io/me1/symbol.png"}, "Obsidian Flames": {"id": "sv3", "logo": "https://images.pokemontcg.io/sv3/logo.png", "symbol": "https://images.pokemontcg.io/sv3/symbol.png"}, "Paldea Evolved": {"id": "sv2", "logo": "https://images.pokemontcg.io/sv2/logo.png", "symbol": "https://images.pokemontcg.io/sv2/symbol.png"}, "Paldean Fates": {"id": "sv4pt5", "logo": "https://images.pokemontcg.io/sv4pt5/logo.png", "symbol": "https://images.pokemontcg.io/sv4pt5/symbol.png"}, "Paradox Rift": {"id": "sv4", "logo": "https://images.pokemontcg.io/sv4/logo.png", "symbol": "https://images.pokemontcg.io/sv4/symbol.png"}, "Perfect Order": {"id": "me3", "logo": "https://images.scrydex.com/pokemon/me3-logo/logo", "symbol": "https://images.scrydex.com/pokemon/me3-symbol/symbol"}, "Phantasmal Flames": {"id": "me2", "logo": "https://images.pokemontcg.io/me2/logo.png", "symbol": "https://images.pokemontcg.io/me2/symbol.png"}, "Prismatic Evolutions": {"id": "sv8pt5", "logo": "https://images.pokemontcg.io/sv8pt5/logo.png", "symbol": "https://images.pokemontcg.io/sv8pt5/symbol.png"}, "Rebel Clash": {"id": "swsh2", "logo": "https://images.pokemontcg.io/swsh2/logo.png", "symbol": "https://images.pokemontcg.io/swsh2/symbol.png"}, "Shining Fates": {"id": "swsh45", "logo": "https://images.pokemontcg.io/swsh45/logo.png", "symbol": "https://images.pokemontcg.io/swsh45/symbol.png"}, "Shrouded Fable": {"id": "sv6pt5", "logo": "https://images.pokemontcg.io/sv6pt5/logo.png", "symbol": "https://images.pokemontcg.io/sv6pt5/symbol.png"}, "Silver Tempest": {"id": "swsh12", "logo": "https://images.pokemontcg.io/swsh12/logo.png", "symbol": "https://images.pokemontcg.io/swsh12/symbol.png"}, "Stellar Crown": {"id": "sv7", "logo": "https://images.pokemontcg.io/sv7/logo.png", "symbol": "https://images.pokemontcg.io/sv7/symbol.png"}, "Surging Sparks": {"id": "sv8", "logo": "https://images.pokemontcg.io/sv8/logo.png", "symbol": "https://images.pokemontcg.io/sv8/symbol.png"}, "S&V Base set": {"id": "base1", "logo": "https://images.pokemontcg.io/base1/logo.png", "symbol": "https://images.pokemontcg.io/base1/symbol.png"}, "Sword and Shield": {"id": "swsh1", "logo": "https://images.pokemontcg.io/swsh1/logo.png", "symbol": "https://images.pokemontcg.io/swsh1/symbol.png"}, "Team Up": {"id": "sm9", "logo": "https://images.pokemontcg.io/sm9/logo.png", "symbol": "https://images.pokemontcg.io/sm9/symbol.png"}, "Temporal Forces": {"id": "sv5", "logo": "https://images.pokemontcg.io/sv5/logo.png", "symbol": "https://images.pokemontcg.io/sv5/symbol.png"}, "Twilight Masquerade": {"id": "sv6", "logo": "https://images.pokemontcg.io/sv6/logo.png", "symbol": "https://images.pokemontcg.io/sv6/symbol.png"}, "Ultra Prism": {"id": "sm5", "logo": "https://images.pokemontcg.io/sm5/logo.png", "symbol": "https://images.pokemontcg.io/sm5/symbol.png"}, "Unbroken Bonds": {"id": "sm10", "logo": "https://images.pokemontcg.io/sm10/logo.png", "symbol": "https://images.pokemontcg.io/sm10/symbol.png"}, "Unified Minds": {"id": "sm11", "logo": "https://images.pokemontcg.io/sm11/logo.png", "symbol": "https://images.pokemontcg.io/sm11/symbol.png"}, "Vivid Voltage": {"id": "swsh4", "logo": "https://images.pokemontcg.io/swsh4/logo.png", "symbol": "https://images.pokemontcg.io/swsh4/symbol.png"}, "White Flare": {"id": "rsv10pt5", "logo": "https://images.pokemontcg.io/rsv10pt5/logo.png", "symbol": "https://images.pokemontcg.io/rsv10pt5/symbol.png"}}


API_KEY             = os.getenv("API_KEY")
GOOGLE_CLIENT_ID    = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET= os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET          = os.getenv("JWT_SECRET")
JWT_ALGORITHM       = "HS256"
JWT_EXPIRY_DAYS     = 30
FRONTEND_URL        = os.getenv("FRONTEND_URL", "https://tcginvest.uk")
DATABASE_URL        = os.getenv("DATABASE_URL")

app = FastAPI(
    title="TCG Invest API",
    description="Private API for tcginvest.uk investor tools",
    version="3.0.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tcginvest.uk",
        "https://www.tcginvest.uk",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://100.107.74.24:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(key: str = Depends(api_key_header)):
    if not key or key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn


# ─── HEALTH ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "tcginvest-api", "version": "3.0.0"}


# ─── SETS ────────────────────────────────────────────────────────────────────

@app.get("/api/sets")
def get_sets(
    era:            Optional[str]   = Query(None),
    recommendation: Optional[str]   = Query(None),
    min_score:      Optional[int]   = Query(None),
    max_box_pct:    Optional[float] = Query(None),
    run_date:       Optional[str]   = Query(None),
    _: str = Depends(require_api_key),
):
    conn = get_db()
    try:
        cur = conn.cursor()
        if run_date:
            resolved_date = run_date
        else:
            cur.execute("SELECT MAX(run_date) as latest FROM monthly_snapshots")
            row = cur.fetchone()
            if not row or not row["latest"]:
                return {"run_date": None, "sets": []}
            resolved_date = row["latest"]

        query = """
            SELECT
                s.id, s.name, s.era, s.date_released, s.print_status,
                s.logo_url, s.booster_img_url, s.etb_img_url,
                s.wizard_id, s.wizard_slug, s.chase_cards_json,
                m.run_date, m.bb_price_gbp, m.set_value_gbp, m.top3_chase,
                m.box_pct, m.chase_pct, m.price_source,
                sc.recommendation, sc.scarcity, sc.liquidity,
                sc.mascot_power, sc.set_depth, sc.decision_score
            FROM sets s
            JOIN monthly_snapshots m ON m.set_id = s.id AND m.run_date = %s
            LEFT JOIN scores sc ON sc.set_id = s.id AND sc.run_date = %s
            WHERE 1=1
        """
        params = [resolved_date, resolved_date]

        if era:
            query += " AND s.era = %s"
            params.append(era)
        if recommendation:
            query += " AND sc.recommendation = %s"
            params.append(recommendation)
        if min_score is not None:
            query += " AND sc.decision_score >= %s"
            params.append(min_score)
        if max_box_pct is not None:
            query += " AND m.box_pct <= %s"
            params.append(max_box_pct)

        query += " ORDER BY sc.decision_score DESC, m.box_pct ASC"

        cur.execute(query, params)
        sets = cur.fetchall()
        return {"run_date": resolved_date, "count": len(sets), "sets": [dict(r) for r in sets]}
    finally:
        conn.close()


@app.get("/api/sets/run-dates")
def get_run_dates(_: str = Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT run_date FROM monthly_snapshots ORDER BY run_date DESC")
        rows = cur.fetchall()
        return {"run_dates": [row["run_date"] for row in rows]}
    finally:
        conn.close()


@app.get("/api/sets/{set_name}/history")
def get_set_history(set_name: str, _: str = Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, era, date_released, print_status FROM sets WHERE name = %s",
            (set_name,)
        )
        set_row = cur.fetchone()
        if not set_row:
            raise HTTPException(status_code=404, detail=f"Set '{set_name}' not found")

        cur.execute("""
            SELECT
                m.run_date, m.bb_price_gbp, m.set_value_gbp, m.top3_chase,
                m.box_pct, m.chase_pct,
                sc.recommendation, sc.decision_score,
                sc.scarcity, sc.liquidity, sc.mascot_power, sc.set_depth
            FROM monthly_snapshots m
            LEFT JOIN scores sc ON sc.set_id = m.set_id AND sc.run_date = m.run_date
            WHERE m.set_id = %s
            ORDER BY m.run_date ASC
        """, (set_row["id"],))
        history = cur.fetchall()

        return {"set": dict(set_row), "history": [dict(row) for row in history]}
    finally:
        conn.close()


@app.get("/api/movers")
def get_movers(_: str = Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT run_date FROM monthly_snapshots ORDER BY run_date DESC LIMIT 2"
        )
        dates = cur.fetchall()

        if len(dates) < 2:
            return {"latest": None, "previous": None, "movers": []}

        latest   = dates[0]["run_date"]
        previous = dates[1]["run_date"]

        cur.execute("""
            SELECT
                s.name,
                s.era,
                curr.bb_price_gbp   AS curr_bb,
                prev.bb_price_gbp   AS prev_bb,
                curr.box_pct        AS curr_box_pct,
                prev.box_pct        AS prev_box_pct,
                curr_sc.decision_score AS curr_score,
                prev_sc.decision_score AS prev_score,
                curr_sc.recommendation AS curr_rec
            FROM sets s
            JOIN monthly_snapshots curr ON curr.set_id = s.id AND curr.run_date = %s
            JOIN monthly_snapshots prev ON prev.set_id = s.id AND prev.run_date = %s
            LEFT JOIN scores curr_sc ON curr_sc.set_id = s.id AND curr_sc.run_date = %s
            LEFT JOIN scores prev_sc ON prev_sc.set_id = s.id AND prev_sc.run_date = %s
            WHERE curr.bb_price_gbp IS NOT NULL AND prev.bb_price_gbp IS NOT NULL
        """, (latest, previous, latest, previous))
        rows = cur.fetchall()

        movers = []
        for row in rows:
            r = dict(row)
            bb_change = bb_change_pct = box_pct_change = score_change = None

            if r["curr_bb"] and r["prev_bb"]:
                bb_change     = round(float(r["curr_bb"]) - float(r["prev_bb"]), 2)
                bb_change_pct = round((bb_change / float(r["prev_bb"])) * 100, 1)

            if r["curr_box_pct"] is not None and r["prev_box_pct"] is not None:
                box_pct_change = round(float(r["curr_box_pct"]) - float(r["prev_box_pct"]), 4)

            if r["curr_score"] is not None and r["prev_score"] is not None:
                score_change = r["curr_score"] - r["prev_score"]

            movers.append({
                "name":           r["name"],
                "era":            r["era"],
                "curr_bb":        r["curr_bb"],
                "prev_bb":        r["prev_bb"],
                "bb_change":      bb_change,
                "bb_change_pct":  bb_change_pct,
                "curr_box_pct":   r["curr_box_pct"],
                "prev_box_pct":   r["prev_box_pct"],
                "box_pct_change": box_pct_change,
                "curr_score":     r["curr_score"],
                "prev_score":     r["prev_score"],
                "score_change":   score_change,
                "curr_rec":       r["curr_rec"],
            })

        return {"latest": latest, "previous": previous, "movers": movers}
    finally:
        conn.close()


@app.get("/api/summary")
def get_summary(_: str = Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MAX(run_date) as latest FROM monthly_snapshots")
        latest = cur.fetchone()["latest"]
        if not latest:
            return {"run_date": None}

        cur.execute("""
            SELECT
                COUNT(*)                                        as total_sets,
                ROUND(AVG(m.box_pct)::numeric, 4)              as avg_box_pct,
                SUM(CASE WHEN sc.recommendation IN
                    ('Strong Buy','Buy') THEN 1 ELSE 0 END)    as buy_count,
                SUM(CASE WHEN sc.recommendation IN
                    ('Sell','Reduce') THEN 1 ELSE 0 END)       as sell_count,
                SUM(CASE WHEN sc.recommendation =
                    'Strong Buy' THEN 1 ELSE 0 END)            as strong_buy_count,
                ROUND(MIN(m.box_pct)::numeric, 4)              as best_box_pct,
                ROUND(MAX(sc.decision_score)::numeric, 0)      as highest_score
            FROM monthly_snapshots m
            LEFT JOIN scores sc ON sc.set_id = m.set_id AND sc.run_date = m.run_date
            WHERE m.run_date = %s
        """, (latest,))
        stats = cur.fetchone()

        cur.execute("SELECT COUNT(*) as etb_count FROM etbs")
        etb_row = cur.fetchone()
        etb_count = etb_row["etb_count"] if etb_row else 0

        cur.execute(
            "SELECT * FROM run_log WHERE run_date = %s ORDER BY id DESC LIMIT 1",
            (latest,)
        )
        run_log = cur.fetchone()

        return {
            "run_date": latest,
            "stats":    {**dict(stats), "etb_count": etb_count},
            "last_run": dict(run_log) if run_log else None,
        }
    finally:
        conn.close()


@app.get("/api/tools")
def get_tools(_: str = Depends(require_api_key)):
    return {
        "tools": [
            {
                "slug":        "tracker",
                "name":        "Booster Box Tracker",
                "description": "Monthly price and investment score tracker across 44+ Pokemon TCG sets",
                "status":      "live",
                "route":       "/tools/tracker",
                "updated":     "monthly",
            },
            {
                "slug":        "etb-tracker",
                "name":        "Pokemon Centre ETB Tracker",
                "description": "Track Pokemon Centre Elite Trainer Box prices, promo card values and PSA premium ratios",
                "status":      "live",
                "route":       "/tools/etb-tracker",
                "updated":     "weekly",
            },
            {
                "slug":        "roi-calculator",
                "name":        "ROI Calculator",
                "description": "Calculate return on investment for sealed product over time",
                "status":      "coming_soon",
                "route":       "/tools/roi",
                "updated":     None,
            },
            {
                "slug":        "price-alerts",
                "name":        "Price Alerts",
                "description": "Get notified when a set drops below your target Box %",
                "status":      "coming_soon",
                "route":       "/tools/alerts",
                "updated":     None,
            },
        ]
    }


# ─── STRIPE ──────────────────────────────────────────────────────────────────

import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID       = os.getenv("STRIPE_PRICE_ID")

from fastapi import Request

@app.post("/api/stripe/checkout")
async def stripe_checkout(request: Request, user=Depends(lambda: None)):
    auth_token = request.cookies.get("auth_token")
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(auth_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT stripe_customer_id, email FROM users WHERE id = %s", (int(payload["sub"]),))
        user_row = cur.fetchone()
    finally:
        conn.close()

    customer_id = user_row["stripe_customer_id"] if user_row else None

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/premium/success",
        cancel_url=f"{FRONTEND_URL}/premium",
        metadata={"user_id": payload["sub"]},
    )
    return {"url": session.url}


@app.post("/api/stripe/portal")
async def stripe_portal(request: Request):
    auth_token = request.cookies.get("auth_token")
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(auth_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT stripe_customer_id FROM users WHERE id = %s", (int(payload["sub"]),))
        user_row = cur.fetchone()
    finally:
        conn.close()

    if not user_row or not user_row["stripe_customer_id"]:
        raise HTTPException(status_code=400, detail="No Stripe customer found")

    session = stripe.billing_portal.Session.create(
        customer=user_row["stripe_customer_id"],
        return_url=f"{FRONTEND_URL}/premium",
    )
    return {"url": session.url}


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    conn = get_db()
    try:
        cur = conn.cursor()
        if event["type"] == "checkout.session.completed":
            session    = event["data"]["object"]
            user_id    = session.get("metadata", {}).get("user_id")
            customer_id= session.get("customer")
            if user_id:
                cur.execute("""
                    UPDATE users SET role='premium', stripe_customer_id=%s, updated_at=NOW()
                    WHERE id=%s
                """, (customer_id, int(user_id)))
                conn.commit()

        elif event["type"] in ("customer.subscription.deleted", "customer.subscription.paused"):
            customer_id = event["data"]["object"].get("customer")
            if customer_id:
                cur.execute("""
                    UPDATE users SET role='free', updated_at=NOW()
                    WHERE stripe_customer_id=%s
                """, (customer_id,))
                conn.commit()
    finally:
        conn.close()

    return {"status": "ok"}


# ─── AUTH ────────────────────────────────────────────────────────────────────

def create_jwt(user_id: int, email: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRY_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(auth_token: str = Cookie(default=None)):
    if not auth_token:
        return None
    try:
        payload = jwt.decode(auth_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

def require_auth(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def require_premium(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if user.get("role") not in ("premium", "admin"):
        raise HTTPException(status_code=403, detail="Premium subscription required")
    return user


@app.get("/auth/google")
def auth_google():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{FRONTEND_URL}/auth/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")


@app.get("/auth/callback")
async def auth_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{FRONTEND_URL}/auth/callback",
                "grant_type": "authorization_code",
            }
        )
        tokens = token_res.json()
        if "error" in tokens:
            raise HTTPException(status_code=400, detail=tokens["error"])

        userinfo_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        userinfo = userinfo_res.json()

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, role FROM users WHERE google_id = %s",
            (userinfo["sub"],)
        )
        existing = cur.fetchone()

        if existing:
            user_id = existing["id"]
            role    = existing["role"]
            cur.execute(
                "UPDATE users SET name=%s, avatar=%s, updated_at=NOW() WHERE id=%s",
                (userinfo.get("name"), userinfo.get("picture"), user_id)
            )
        else:
            cur.execute(
                "INSERT INTO users (google_id, email, name, avatar, role) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (userinfo["sub"], userinfo["email"], userinfo.get("name"), userinfo.get("picture"), "free")
            )
            user_id = cur.fetchone()["id"]
            role    = "free"
        conn.commit()
    finally:
        conn.close()

    token = create_jwt(user_id, userinfo["email"], role)
    response = RedirectResponse(url=f"{FRONTEND_URL}/?login=success")
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30
    )
    return response


@app.get("/auth/me")
def auth_me(user=Depends(get_current_user)):
    if not user:
        return JSONResponse({"authenticated": False})
    return {
        "authenticated": True,
        "email":   user.get("email"),
        "role":    user.get("role"),
        "user_id": user.get("sub")
    }


@app.post("/auth/logout")
def auth_logout():
    response = JSONResponse({"success": True})
    response.delete_cookie("auth_token")
    return response


# ─── WATCHLIST ───────────────────────────────────────────────────────────────

@app.get("/api/watchlist")
def get_watchlist(user=Depends(require_auth)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT set_name, created_at FROM watchlist WHERE user_id = %s ORDER BY created_at DESC",
            (int(user["sub"]),)
        )
        rows = cur.fetchall()
        return {"watchlist": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.post("/api/watchlist/{set_name}")
def add_to_watchlist(set_name: str, user=Depends(require_auth)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) as c FROM watchlist WHERE user_id = %s",
            (int(user["sub"]),)
        )
        count = cur.fetchone()["c"]

        if count >= 5 and user.get("role") == "free":
            raise HTTPException(status_code=403, detail="Free tier limited to 5 watchlist items. Upgrade to premium for unlimited.")

        cur.execute(
            "INSERT INTO watchlist (user_id, set_name) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (int(user["sub"]), set_name)
        )
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


@app.delete("/api/watchlist/{set_name}")
def remove_from_watchlist(set_name: str, user=Depends(require_auth)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM watchlist WHERE user_id = %s AND set_name = %s",
            (int(user["sub"]), set_name)
        )
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


# ─── ETB TRACKER ─────────────────────────────────────────────────────────────

@app.get("/api/etbs")
def get_etbs(_: str = Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                e.id, e.name, e.promo_pokemon, e.promo_card_code,
                e.is_stamped_promo, e.pack_count, e.msrp_gbp,
                e.drop_type, e.available_date, e.in_stock,
                e.promo_desirability, e.set_desirability,
                e.drop_scarcity, e.promo_artist,
                s.name as set_name, s.era, s.logo_url,
                p.ebay_avg_sold_gbp, p.sealed_premium_pct,
                p.raw_promo_gbp, p.psa10_promo_gbp,
                p.psa_premium_ratio, p.snapshot_date
            FROM etbs e
            LEFT JOIN sets s ON s.id = e.set_id
            LEFT JOIN LATERAL (
                SELECT * FROM etb_price_snapshots
                WHERE etb_id = e.id
                ORDER BY snapshot_date DESC
                LIMIT 1
            ) p ON true
            ORDER BY e.available_date DESC
        """)
        rows = cur.fetchall()
        return {"count": len(rows), "etbs": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.get("/api/etbs/{etb_id}/history")
def get_etb_history(etb_id: int, _: str = Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM etbs WHERE id = %s", (etb_id,))
        etb = cur.fetchone()
        if not etb:
            raise HTTPException(status_code=404, detail="ETB not found")

        cur.execute("""
            SELECT snapshot_date, ebay_avg_sold_gbp, ebay_sold_count,
                   sealed_premium_pct, raw_promo_gbp, psa10_promo_gbp,
                   psa_premium_ratio, price_source
            FROM etb_price_snapshots
            WHERE etb_id = %s
            ORDER BY snapshot_date ASC
        """, (etb_id,))
        history = cur.fetchall()

        return {"etb": dict(etb), "history": [dict(r) for r in history]}
    finally:
        conn.close()


# ─── ETB WATCHLIST ───────────────────────────────────────────────────────────

@app.get("/api/etb-watchlist")
def get_etb_watchlist(user=Depends(require_auth)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ew.etb_id, e.name, e.promo_pokemon, ew.created_at
            FROM etb_watchlist ew
            JOIN etbs e ON e.id = ew.etb_id
            WHERE ew.user_id = %s
            ORDER BY ew.created_at DESC
        """, (int(user["sub"]),))
        rows = cur.fetchall()
        return {"watchlist": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.post("/api/etb-watchlist/{etb_id}")
def add_to_etb_watchlist(etb_id: int, user=Depends(require_auth)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) as c FROM etb_watchlist WHERE user_id = %s",
            (int(user["sub"]),)
        )
        count = cur.fetchone()["c"]
        if count >= 3 and user.get("role") == "free":
            raise HTTPException(status_code=403, detail="Free tier limited to 3 ETB watchlist items. Upgrade to premium for unlimited.")
        cur.execute(
            "SELECT id FROM etbs WHERE id = %s",
            (etb_id,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="ETB not found")
        cur.execute(
            "INSERT INTO etb_watchlist (user_id, etb_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (int(user["sub"]), etb_id)
        )
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


@app.delete("/api/etb-watchlist/{etb_id}")
def remove_from_etb_watchlist(etb_id: int, user=Depends(require_auth)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM etb_watchlist WHERE user_id = %s AND etb_id = %s",
            (int(user["sub"]), etb_id)
        )
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


# ─── ETB MOVERS ──────────────────────────────────────────────────────────────

@app.get("/api/etb-movers")
def get_etb_movers(_: str = Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT snapshot_date FROM etb_price_snapshots
            ORDER BY snapshot_date DESC LIMIT 2
        """)
        dates = cur.fetchall()
        if len(dates) < 2:
            return {"latest": None, "previous": None, "movers": []}

        latest   = dates[0]["snapshot_date"]
        previous = dates[1]["snapshot_date"]

        cur.execute("""
            SELECT
                e.id, e.name, e.promo_pokemon,
                curr.ebay_avg_sold_gbp AS curr_price,
                prev.ebay_avg_sold_gbp AS prev_price,
                curr.sealed_premium_pct AS curr_premium
            FROM etbs e
            JOIN etb_price_snapshots curr ON curr.etb_id = e.id AND curr.snapshot_date = %s
            JOIN etb_price_snapshots prev ON prev.etb_id = e.id AND prev.snapshot_date = %s
            WHERE curr.ebay_avg_sold_gbp IS NOT NULL
            AND prev.ebay_avg_sold_gbp IS NOT NULL
        """, (latest, previous))
        rows = cur.fetchall()

        movers = []
        for row in rows:
            r = dict(row)
            if r["curr_price"] and r["prev_price"]:
                change     = round(float(r["curr_price"]) - float(r["prev_price"]), 2)
                change_pct = round((change / float(r["prev_price"])) * 100, 1)
                movers.append({
                    "id":           r["id"],
                    "name":         r["name"],
                    "promo_pokemon":r["promo_pokemon"],
                    "curr_price":   float(r["curr_price"]),
                    "prev_price":   float(r["prev_price"]),
                    "change":       change,
                    "change_pct":   change_pct,
                    "curr_premium": float(r["curr_premium"]) if r["curr_premium"] else None,
                })

        return {
            "latest":   str(latest),
            "previous": str(previous),
            "movers":   sorted(movers, key=lambda x: abs(x["change"]), reverse=True)
        }
    finally:
        conn.close()


@app.post("/api/events")
async def track_event(request: Request, user=Depends(get_current_user)):
    body = await request.json()
    action = body.get("action", "")
    page = body.get("page", "")
    session_id = body.get("session_id", "")
    if not action:
        return {"ok": False}
    user_id = int(user["sub"]) if user else None
    ip_hash = hashlib.sha256(request.client.host.encode()).hexdigest()[:16]
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO page_events (user_id, session_id, page, action, ip_hash) VALUES (%s, %s, %s, %s, %s)",
            (user_id, session_id, page, action, ip_hash)
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()



# ─────────────────────────────────────────────
# PRICE ALERTS
# ─────────────────────────────────────────────

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "alerts@tcginvest.uk")


def _send_alert_email(to_email: str, product_name: str, threshold_gbp: float, current_price: float, product_type: str):
    if product_type == "set":
        slug = product_name.lower().replace(" & ", "-and-").replace("&", "and").replace(" ", "-").replace(":", "").replace("'", "")
        path = f"/sets/{slug}"
    else:
        slug = product_name.lower().replace("pokemon centre ", "pc-").replace(" & ", "-and-").replace("&", "and").replace(" ", "-").replace(":", "").replace("'", "")
        path = f"/etbs/{slug}"
    url = f"https://tcginvest.uk{path}"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;">
      <div style="background:#1a1a2e;padding:20px;border-radius:8px 8px 0 0;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:20px;">&#128276; TCGInvest Price Alert</h1>
      </div>
      <div style="background:#f9f9f9;padding:24px;border-radius:0 0 8px 8px;border:1px solid #e0e0e0;">
        <p style="font-size:16px;color:#333;margin-top:0;">Good news &#8212; your price alert has triggered!</p>
        <div style="background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:16px;margin:16px 0;">
          <p style="margin:0 0 4px;color:#666;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Product</p>
          <p style="margin:0;font-size:18px;font-weight:bold;color:#1a1a2e;">{product_name}</p>
        </div>
        <table style="width:100%;border-collapse:separate;border-spacing:8px;margin:16px 0;">
          <tr>
            <td style="background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:16px;text-align:center;width:50%;">
              <p style="margin:0 0 4px;color:#666;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Your threshold</p>
              <p style="margin:0;font-size:24px;font-weight:bold;color:#e53e3e;">&#163;{threshold_gbp:.2f}</p>
            </td>
            <td style="background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:16px;text-align:center;width:50%;">
              <p style="margin:0 0 4px;color:#666;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Current price</p>
              <p style="margin:0;font-size:24px;font-weight:bold;color:#38a169;">&#163;{current_price:.2f}</p>
            </td>
          </tr>
        </table>
        <a href="{url}" style="display:block;background:#1a1a2e;color:#fff;text-align:center;padding:14px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:16px;margin:20px 0;">View {product_name} &#8594;</a>
        <p style="font-size:12px;color:#999;text-align:center;margin:0;">
          This alert has been deactivated. Visit <a href="https://tcginvest.uk/account/alerts" style="color:#666;">your alerts page</a> to set a new one.
        </p>
      </div>
    </div>
    """
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={"from": FROM_EMAIL, "to": [to_email], "subject": f"Price Alert: {product_name} is now £{current_price:.2f}", "html": html},
            timeout=10
        )
        return resp.status_code == 200
    except Exception:
        return False


@app.post("/api/alerts")
async def create_alert(request: Request, user=Depends(require_auth)):
    body = await request.json()
    product_type = body.get("product_type")
    product_id = body.get("product_id")
    product_name = body.get("product_name")
    threshold_gbp = body.get("threshold_gbp")

    if not all([product_type, product_id is not None, product_name, threshold_gbp is not None]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    if product_type not in ("set", "etb"):
        raise HTTPException(status_code=400, detail="Invalid product_type")
    try:
        threshold_gbp = float(threshold_gbp)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid threshold")

    user_id = int(user["sub"])
    conn = get_db()
    try:
        cur = conn.cursor()
        if user.get("role", "free") != "premium":
            cur.execute("SELECT COUNT(*) AS cnt FROM price_alerts WHERE user_id = %s AND triggered = FALSE", (user_id,))
            row = cur.fetchone()
            count = row["cnt"] if isinstance(row, dict) else row[0]
            if count >= 1:
                raise HTTPException(status_code=403, detail="FREE_LIMIT_REACHED")

        cur.execute("""
            INSERT INTO price_alerts (user_id, product_type, product_id, product_name, threshold_gbp)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (user_id, product_type, int(product_id), product_name, threshold_gbp))
        row = cur.fetchone()
        alert_id = row["id"] if isinstance(row, dict) else row[0]
        conn.commit()
        return {"id": alert_id, "message": "Alert created"}
    finally:
        conn.close()


@app.get("/api/alerts")
async def get_alerts(user=Depends(require_auth)):
    user_id = int(user["sub"])
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, product_type, product_id, product_name, threshold_gbp,
                   triggered, triggered_at, created_at
            FROM price_alerts WHERE user_id = %s ORDER BY created_at DESC
        """, (user_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, user=Depends(require_auth)):
    user_id = int(user["sub"])
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM price_alerts WHERE id = %s AND user_id = %s RETURNING id",
            (alert_id, user_id)
        )
        deleted = cur.fetchone()
        conn.commit()
        if not deleted:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"message": "Alert deleted"}
    finally:
        conn.close()


@app.post("/api/alerts/run-checks")
async def run_alert_checks(request: Request):
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT pa.id, pa.product_type, pa.product_id, pa.product_name,
                   pa.threshold_gbp, u.email
            FROM price_alerts pa
            JOIN users u ON u.id = pa.user_id
            WHERE pa.triggered = FALSE
        """)
        alerts = cur.fetchall()

        triggered_count = 0
        for row in alerts:
            alert_id = row["id"]; product_type = row["product_type"]
            product_id = row["product_id"]; product_name = row["product_name"]
            threshold_gbp = row["threshold_gbp"]; email = row["email"]
            current_price = None

            try:
                if product_type == "set":
                    cur.execute("SELECT bb_price_gbp FROM sets WHERE id = %s", (product_id,))
                else:
                    cur.execute("SELECT ebay_avg_sold_gbp FROM etb_price_snapshots WHERE etb_id = %s ORDER BY snapshot_date DESC LIMIT 1", (product_id,))
                price_row = cur.fetchone()
                if price_row:
                    val = price_row["bb_price_gbp"] if product_type == "set" else price_row["ebay_avg_sold_gbp"]
                    if val:
                        current_price = float(val)
            except Exception:
                continue

            if current_price is not None and current_price <= float(threshold_gbp):
                sent = _send_alert_email(email, product_name, float(threshold_gbp), current_price, product_type)
                if sent:
                    cur.execute("UPDATE price_alerts SET triggered = TRUE, triggered_at = NOW() WHERE id = %s", (alert_id,))
                    triggered_count += 1

        conn.commit()
        return {"checked": len(alerts), "triggered": triggered_count}
    finally:
        conn.close()


# ─────────────────────────────────────────────
# DIGEST FEATURE (added v5.4)
# ─────────────────────────────────────────────

@app.on_event("startup")
async def run_digest_migrations():
    """Add digest_frequency to users and create digest_log if not exists."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    _db_url = os.environ.get("DATABASE_URL", "")
    conn = psycopg2.connect(_db_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    # digest_frequency column added via one-time migration (run as postgres OS user)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS digest_log (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            sets_count INTEGER DEFAULT 0,
            etbs_count INTEGER DEFAULT 0
        );
    """)
    try:
        cur.execute("GRANT ALL ON TABLE digest_log TO tcginvest;")
        cur.execute("GRANT USAGE, SELECT ON SEQUENCE digest_log_id_seq TO tcginvest;")
    except Exception:
        pass
    conn.commit()
    cur.close()
    conn.close()


@app.get("/api/digest/preferences")
async def get_digest_preferences(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    import psycopg2 as _psycopg2
    from psycopg2.extras import RealDictCursor as _RDC
    import os as _os
    conn = _psycopg2.connect(_os.environ.get("DATABASE_URL",""), cursor_factory=_RDC)
    cur = conn.cursor()
    cur.execute("SELECT digest_frequency FROM users WHERE id = %s", (user["id"],))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {"digest_frequency": row["digest_frequency"] if row else "weekly"}


@app.put("/api/digest/preferences")
async def update_digest_preferences(request: Request, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    body = await request.json()
    frequency = body.get("digest_frequency", "weekly")
    if frequency not in ("daily", "weekly", "monthly", "off"):
        raise HTTPException(status_code=400, detail="Invalid frequency. Must be daily, weekly, monthly, or off.")
    import psycopg2 as _psycopg2
    from psycopg2.extras import RealDictCursor as _RDC
    import os as _os
    conn = _psycopg2.connect(_os.environ.get("DATABASE_URL",""), cursor_factory=_RDC)
    cur = conn.cursor()
    cur.execute("UPDATE users SET digest_frequency = %s WHERE id = %s", (frequency, user["id"]))
    conn.commit()
    cur.close()
    conn.close()
    return {"digest_frequency": frequency, "updated": True}


@app.post("/api/digest/run")
async def run_digest(request: Request):
    """Internal cron endpoint — requires X-API-Key."""
    api_key = request.headers.get("X-API-Key")
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    import httpx, os, datetime

    frequency_filter = request.query_params.get("frequency", "weekly")
    if frequency_filter not in ("daily", "weekly", "monthly"):
        raise HTTPException(status_code=400, detail="Invalid frequency filter")

    import psycopg2 as _psycopg2
    from psycopg2.extras import RealDictCursor as _RDC
    import os as _os
    conn = _psycopg2.connect(_os.environ.get("DATABASE_URL",""), cursor_factory=_RDC)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT u.id, u.email, u.digest_frequency
        FROM users u
        WHERE u.digest_frequency = %s
        AND (
            EXISTS (SELECT 1 FROM watchlist w WHERE w.user_id = u.id)
            OR EXISTS (SELECT 1 FROM etb_watchlist ew WHERE ew.user_id = u.id)
        )
    """, (frequency_filter,))
    users = cur.fetchall()

    sent = 0
    errors = []

    for user_row in users:
        uid = user_row["id"]
        email = user_row["email"]
        try:
            # Booster box watchlist
            cur.execute("""
                SELECT
                    s.name AS set_name,
                    ms.bb_price_gbp AS current_price,
                    sc.recommendation,
                    prev_ms.bb_price_gbp AS prev_price
                FROM watchlist w
                JOIN sets s ON s.name = w.set_name
                JOIN monthly_snapshots ms ON ms.set_id = s.id
                    AND ms.run_date = (SELECT MAX(run_date) FROM monthly_snapshots)
                LEFT JOIN scores sc ON sc.set_id = s.id
                    AND sc.run_date = ms.run_date
                LEFT JOIN LATERAL (
                    SELECT bb_price_gbp FROM monthly_snapshots
                    WHERE set_id = s.id
                    AND run_date < (SELECT MAX(run_date) FROM monthly_snapshots)
                    ORDER BY run_date DESC LIMIT 1
                ) prev_ms ON true
                WHERE w.user_id = %s
                ORDER BY s.name
            """, (uid,))
            sets_rows = cur.fetchall()

            # ETB watchlist
            cur.execute("""
                SELECT
                    e.name,
                    e.id AS etb_id,
                    ps.ebay_avg_sold_gbp AS current_price,
                    e.msrp_gbp,
                    prev_ps.ebay_avg_sold_gbp AS prev_price
                FROM etb_watchlist ew
                JOIN etbs e ON e.id = ew.etb_id
                LEFT JOIN LATERAL (
                    SELECT ebay_avg_sold_gbp FROM etb_price_snapshots
                    WHERE etb_id = e.id ORDER BY snapshot_date DESC LIMIT 1
                ) ps ON true
                LEFT JOIN LATERAL (
                    SELECT ebay_avg_sold_gbp FROM etb_price_snapshots
                    WHERE etb_id = e.id AND snapshot_date < NOW() - INTERVAL '6 days'
                    ORDER BY snapshot_date DESC LIMIT 1
                ) prev_ps ON true
                WHERE ew.user_id = %s
                ORDER BY e.name
            """, (uid,))
            etb_rows = cur.fetchall()

            if not sets_rows and not etb_rows:
                continue

            html = _build_digest_email(sets_rows, etb_rows, frequency_filter)
            label = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}.get(frequency_filter, "Weekly")
            date_str = datetime.date.today().strftime("%d %b %Y")
            subject = f"Your TCGInvest {label} Watchlist — {date_str}"

            resend_key = os.environ.get("RESEND_API_KEY", "")
            from_email = os.environ.get("FROM_EMAIL", "alerts@tcginvest.uk")
            resp = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json={"from": f"TCG Invest <{from_email}>", "to": [email], "subject": subject, "html": html},
                timeout=15
            )
            if resp.status_code in (200, 201, 200):
                cur.execute(
                    "INSERT INTO digest_log (user_id, sets_count, etbs_count) VALUES (%s, %s, %s)",
                    (uid, len(sets_rows), len(etb_rows))
                )
                conn.commit()
                sent += 1
            else:
                errors.append({"email": email, "status": resp.status_code})
        except Exception as e:
            errors.append({"email": email, "error": str(e)})

    cur.close()
    conn.close()
    return {"sent": sent, "errors": errors, "frequency": frequency_filter}


def _build_digest_email(sets_rows, etb_rows, frequency: str) -> str:
    def price_row(current, prev):
        if current is None:
            return "<span style='color:#888'>No data</span>"
        if prev is None or prev == 0:
            return f"<b>£{current:.2f}</b>"
        pct = ((current - prev) / prev) * 100
        if abs(pct) < 0.1:
            ch = "<span style='color:#888'>—</span>"
        elif pct > 0:
            ch = f"<span style='color:#22c55e'>▲ +{pct:.1f}%</span>"
        else:
            ch = f"<span style='color:#ef4444'>▼ {pct:.1f}%</span>"
        return f"<b>£{current:.2f}</b> {ch}"

    def signal_badge(rec):
        if not rec:
            return "—"
        c = {"Strong Buy": "#16a34a", "Buy": "#22c55e", "Hold": "#f59e0b",
             "Sell": "#ef4444", "Strong Sell": "#dc2626"}.get(rec, "#888")
        return f"<span style='background:{c};color:#fff;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:700'>{rec}</span>"

    def msrp_badge(current, msrp):
        if not current or not msrp or msrp == 0:
            return "—"
        pct = ((current - msrp) / msrp) * 100
        col = "#22c55e" if pct >= 0 else "#ef4444"
        sign = "+" if pct >= 0 else ""
        return f"<span style='color:{col};font-weight:600'>{sign}{pct:.0f}%</span>"

    sets_html = ""
    if sets_rows:
        rows = "".join(f"""
          <tr>
            <td style='padding:10px 8px;border-bottom:1px solid #222'>
              <a href='https://tcginvest.uk/sets/{r["set_name"].lower().replace(" & ", "-and-").replace("&", "and").replace(" ", "-").replace("'", "").replace(":", "")}'
                 style='color:#facc15;text-decoration:none;font-weight:600'>{r["set_name"]}</a>
            </td>
            <td style='padding:10px 8px;border-bottom:1px solid #222;text-align:right'>{price_row(r["current_price"], r["prev_price"])}</td>
            <td style='padding:10px 8px;border-bottom:1px solid #222;text-align:center'>{signal_badge(r["recommendation"])}</td>
          </tr>""" for r in sets_rows)
        sets_html = f"""
        <h2 style='color:#facc15;font-size:15px;margin:28px 0 10px'>📦 Booster Box Watchlist</h2>
        <table width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse;font-size:13px;color:#e5e7eb'>
          <tr style='color:#6b7280;font-size:11px;text-transform:uppercase'>
            <th style='padding:6px 8px;text-align:left'>Set</th>
            <th style='padding:6px 8px;text-align:right'>Price (7d Δ)</th>
            <th style='padding:6px 8px;text-align:center'>Signal</th>
          </tr>{rows}
        </table>"""

    etbs_html = ""
    if etb_rows:
        rows = "".join(f"""
          <tr>
            <td style='padding:10px 8px;border-bottom:1px solid #222;color:#e5e7eb;font-weight:600'>{r["name"]}</td>
            <td style='padding:10px 8px;border-bottom:1px solid #222;text-align:right'>{price_row(r["current_price"], r["prev_price"])}</td>
            <td style='padding:10px 8px;border-bottom:1px solid #222;text-align:right'>{msrp_badge(r["current_price"], r["msrp_gbp"])}</td>
          </tr>""" for r in etb_rows)
        etbs_html = f"""
        <h2 style='color:#facc15;font-size:15px;margin:28px 0 10px'>🎴 ETB Watchlist</h2>
        <table width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse;font-size:13px;color:#e5e7eb'>
          <tr style='color:#6b7280;font-size:11px;text-transform:uppercase'>
            <th style='padding:6px 8px;text-align:left'>ETB</th>
            <th style='padding:6px 8px;text-align:right'>Sealed Price (7d Δ)</th>
            <th style='padding:6px 8px;text-align:right'>vs MSRP</th>
          </tr>{rows}
        </table>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'></head>
<body style='margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'>
<table width='100%' cellpadding='0' cellspacing='0'>
<tr><td align='center' style='padding:32px 16px'>
<table width='600' cellpadding='0' cellspacing='0' style='max-width:600px;width:100%'>
  <tr><td style='background:#111;border-radius:12px 12px 0 0;padding:24px 32px;border-bottom:1px solid #1f1f1f;text-align:center'>
    <div style='font-size:22px;font-weight:800;color:#facc15'>TCG<span style='color:#fff'>Invest</span></div>
    <div style='color:#9ca3af;font-size:13px;margin-top:4px'>Your Watchlist Digest</div>
  </td></tr>
  <tr><td style='background:#111;padding:24px 32px'>
    <p style='color:#d1d5db;font-size:14px;margin:0'>Here's your update on the sets and ETBs you're watching.</p>
    {sets_html}
    {etbs_html}
    <div style='margin:28px 0 0;text-align:center'>
      <a href='https://tcginvest.uk/tools/tracker'
         style='display:inline-block;background:#facc15;color:#000;font-weight:700;font-size:14px;padding:12px 28px;border-radius:8px;text-decoration:none'>
        View Full Analysis →
      </a>
    </div>
  </td></tr>
  <tr><td style='background:#0d0d0d;border-radius:0 0 12px 12px;padding:18px 32px;text-align:center;border-top:1px solid #1a1a1a'>
    <p style='color:#6b7280;font-size:11px;margin:0'>
      You're receiving this because you have items in your TCGInvest watchlist.<br>
      <a href='https://tcginvest.uk/account/preferences' style='color:#9ca3af'>Manage email preferences</a> ·
      <a href='https://tcginvest.uk' style='color:#9ca3af'>tcginvest.uk</a>
    </p>
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""
