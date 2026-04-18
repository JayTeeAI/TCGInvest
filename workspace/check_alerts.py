#!/usr/bin/env python3
"""
TCGInvest — Price Alert Checker
Runs daily at 09:15 via cron.
Calls the internal API endpoint to check all untriggered alerts.
Logs to /root/.openclaw/logs/alerts.log
"""
import os, sys, httpx, logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/root/.openclaw/api/.env")

LOG_FILE = "/root/.openclaw/logs/alerts.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def main():
    api_key = os.getenv("API_KEY")
    if not api_key:
        logging.error("API_KEY not set — aborting")
        sys.exit(1)

    try:
        resp = httpx.post(
            "http://127.0.0.1:8000/api/alerts/run-checks",
            headers={"X-API-Key": api_key},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            logging.info(f"Alert check complete — checked: {data.get('checked', 0)}, triggered: {data.get('triggered', 0)}")
        else:
            logging.error(f"Alert check failed — status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logging.error(f"Alert check exception: {e}")

if __name__ == "__main__":
    main()
