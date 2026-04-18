#!/usr/bin/env python3
"""
TCGInvest — Watchlist digest sender.
Reads digest_frequency from .env to decide which users get emails today.
Cron schedule:
  Daily:   15 9 * * *   (09:15 every day)
  Weekly:  runs daily but only sends to digest_frequency='daily' each day,
           'weekly' on Sundays, 'monthly' on 1st of month.
"""
import os, sys, httpx, datetime, logging

LOG_FILE = "/root/.openclaw/logs/digest.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger("digest")

# Load .env
env_path = "/root/.openclaw/api/.env"
env = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()

API_KEY = env.get("API_KEY", "")
API_BASE = "http://127.0.0.1:8000"

def should_send(frequency: str, today: datetime.date) -> bool:
    if frequency == "daily":
        return True
    if frequency == "weekly":
        return today.weekday() == 6  # Sunday
    if frequency == "monthly":
        return today.day == 1
    return False

def run():
    today = datetime.date.today()
    log.info(f"Digest run started — {today} (weekday={today.weekday()})")

    for freq in ("daily", "weekly", "monthly"):
        if not should_send(freq, today):
            log.info(f"Skipping {freq} — not due today")
            continue
        log.info(f"Sending {freq} digests...")
        try:
            resp = httpx.post(
                f"{API_BASE}/api/digest/run?frequency={freq}",
                headers={"X-API-Key": API_KEY},
                timeout=120
            )
            data = resp.json()
            log.info(f"{freq}: sent={data.get('sent',0)} errors={data.get('errors',[])}")
        except Exception as e:
            log.error(f"{freq} digest failed: {e}")

    log.info("Digest run complete")

if __name__ == "__main__":
    run()
