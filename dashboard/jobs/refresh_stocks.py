"""Daily stock-briefing job — the real version of NEO-30's scheduled stub.

Refreshes every stock's AI briefing once a day. It reads the watchlist from the
*deployed dashboard's own API* and writes results back the same way, so it works
regardless of where data lives and reuses the app's login.

**Cost:** when an Anthropic key is set, it generates all briefings in a single
**Batch API** request — 50% cheaper than live calls — then writes each result
back via /api/stocks/set-briefing. Without a key (or if batching fails) it falls
back to the per-stock live path (/api/stocks/refresh), which mocks when no key.

Point a Render Cron Job at it:

    NEO_APP_URL            https://neo-dashboard-xxxx.onrender.com
    DASHBOARD_USER         the app's login user
    DASHBOARD_PASS         the app's login password
    NEO_ANTHROPIC_API_KEY  to use the (cheaper) Batch path; omit for the mock path

    python -m dashboard.jobs.refresh_stocks

See docs/DEPLOY.md for the cron-job setup. Safe to run by hand to test.
"""
from __future__ import annotations

import json
import os
import sys
import time

import requests

ANTHROPIC_KEY = os.environ.get("NEO_ANTHROPIC_API_KEY")
_AH = {"x-api-key": ANTHROPIC_KEY or "", "anthropic-version": "2023-06-01",
       "content-type": "application/json"}
_POLL_SECS = 30
_MAX_WAIT_SECS = 45 * 60  # batches usually finish in minutes; cap so the job exits


def _watchlist(base: str, auth) -> list[dict]:
    """Flatten the watchlist into [{sector_id, name, ticker}, …]."""
    data = requests.get(f"{base}/api/stocks", auth=auth, timeout=30).json()
    out = []
    for sec in data.get("sectors", []):
        for st in sec.get("stocks", []):
            if st.get("name"):
                out.append({"sector_id": sec.get("id"), "name": st["name"],
                            "ticker": st.get("ticker", "") or ""})
    return out


def _live_fallback(base: str, auth, stocks: list[dict]) -> int:
    """Old per-stock path: one live (or mock) call each via /api/stocks/refresh."""
    done = failed = 0
    for st in stocks:
        try:
            r = requests.post(f"{base}/api/stocks/refresh", auth=auth, json=st, timeout=60)
            ok = r.ok and r.json().get("ok")
        except Exception as e:
            ok = False
            print(f"  error {st['name']}: {e}", file=sys.stderr)
        print(("  ok   " if ok else "  FAIL ") + st["name"])
        done += 1 if ok else 0
        failed += 0 if ok else 1
    print(f"Refreshed {done} briefing(s), {failed} failed (live path).")
    return 0 if failed == 0 else 1


def _run_batch(base: str, auth, stocks: list[dict]) -> int:
    """Generate every briefing in one Batch API request (50% off), then write
    each result back via /api/stocks/set-briefing."""
    from dashboard.stocks import ANTHROPIC_MODEL, briefing_prompt

    reqs = [{
        "custom_id": f"s{i}",
        "params": {"model": ANTHROPIC_MODEL, "max_tokens": 400,
                   "messages": [{"role": "user", "content": briefing_prompt(st["name"], st["ticker"])}]},
    } for i, st in enumerate(stocks)]

    create = requests.post("https://api.anthropic.com/v1/messages/batches",
                           headers=_AH, json={"requests": reqs}, timeout=60)
    create.raise_for_status()
    batch_id = create.json()["id"]
    print(f"Submitted batch {batch_id} ({len(reqs)} stocks). Waiting…")

    waited = 0
    while True:
        time.sleep(_POLL_SECS)
        waited += _POLL_SECS
        b = requests.get(f"https://api.anthropic.com/v1/messages/batches/{batch_id}",
                         headers=_AH, timeout=30).json()
        if b.get("processing_status") == "ended":
            break
        if waited >= _MAX_WAIT_SECS:
            print(f"Batch {batch_id} not finished after {waited // 60} min — "
                  "it'll be picked up by tomorrow's run.", file=sys.stderr)
            return 1

    results = requests.get(b["results_url"], headers=_AH, timeout=60)
    results.raise_for_status()
    done = failed = 0
    for line in results.text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        idx = int(row["custom_id"][1:])  # "s0" -> 0
        st = stocks[idx]
        res = row.get("result", {})
        if res.get("type") != "succeeded":
            failed += 1
            print(f"  FAIL {st['name']}: {res.get('type')}", file=sys.stderr)
            continue
        text = "".join(b.get("text", "") for b in res["message"]["content"]
                       if b.get("type") == "text").strip()
        try:
            w = requests.post(f"{base}/api/stocks/set-briefing", auth=auth,
                              json={**st, "update": text}, timeout=30)
            ok = w.ok and w.json().get("ok")
        except Exception as e:
            ok = False
            print(f"  write error {st['name']}: {e}", file=sys.stderr)
        print(("  ok   " if ok else "  FAIL ") + st["name"])
        done += 1 if ok else 0
        failed += 0 if ok else 1

    print(f"Refreshed {done} briefing(s), {failed} failed (batch path, ~50% cost).")
    return 0 if failed == 0 else 1


def main() -> int:
    base = (os.environ.get("NEO_APP_URL") or "").rstrip("/")
    user = os.environ.get("DASHBOARD_USER")
    pw = os.environ.get("DASHBOARD_PASS")
    if not (base and user and pw):
        print("Set NEO_APP_URL, DASHBOARD_USER and DASHBOARD_PASS.", file=sys.stderr)
        return 1

    auth = (user, pw)
    try:
        stocks = _watchlist(base, auth)
    except Exception as e:
        print(f"Couldn't read the watchlist: {e}", file=sys.stderr)
        return 1

    if not stocks:
        print("Watchlist is empty — nothing to refresh.")
        return 0

    if not ANTHROPIC_KEY:
        print("No NEO_ANTHROPIC_API_KEY — using the live/mock path.")
        return _live_fallback(base, auth, stocks)

    try:
        return _run_batch(base, auth, stocks)
    except Exception as e:
        print(f"Batch path failed ({e}); falling back to live calls.", file=sys.stderr)
        return _live_fallback(base, auth, stocks)


if __name__ == "__main__":
    raise SystemExit(main())
