"""Daily stock-briefing job — the real version of NEO-30's scheduled stub.

Refreshes every stock's AI briefing once a day. It calls the *deployed
dashboard's own API* rather than touching storage directly, so it works
regardless of where data lives (ephemeral dir or a persistent disk) and reuses
the app's Anthropic key and login. Point a Render Cron Job at it:

    NEO_APP_URL      https://neo-dashboard-xxxx.onrender.com   (no trailing slash needed)
    DASHBOARD_USER   the app's login user
    DASHBOARD_PASS   the app's login password

    python -m dashboard.jobs.refresh_stocks

See docs/DEPLOY.md for the cron-job setup. Safe to run by hand to test.
"""
from __future__ import annotations

import os
import sys

import requests


def main() -> int:
    base = (os.environ.get("NEO_APP_URL") or "").rstrip("/")
    user = os.environ.get("DASHBOARD_USER")
    pw = os.environ.get("DASHBOARD_PASS")
    if not (base and user and pw):
        print("Set NEO_APP_URL, DASHBOARD_USER and DASHBOARD_PASS.", file=sys.stderr)
        return 1

    auth = (user, pw)
    try:
        data = requests.get(f"{base}/api/stocks", auth=auth, timeout=30).json()
    except Exception as e:
        print(f"Couldn't read the watchlist: {e}", file=sys.stderr)
        return 1

    done = failed = 0
    for sector in data.get("sectors", []):
        for stock in sector.get("stocks", []):
            payload = {"sector_id": sector.get("id"), "name": stock.get("name"),
                       "ticker": stock.get("ticker", "")}
            try:
                r = requests.post(f"{base}/api/stocks/refresh", auth=auth, json=payload, timeout=60)
                ok = r.ok and r.json().get("ok")
            except Exception as e:
                ok = False
                print(f"  error {stock.get('name')}: {e}", file=sys.stderr)
            print(("  ok   " if ok else "  FAIL ") + str(stock.get("name")))
            done += 1 if ok else 0
            failed += 0 if ok else 1

    print(f"Refreshed {done} briefing(s), {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
