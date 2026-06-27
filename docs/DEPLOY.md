# Deploying the dashboard (Mariah's guide)

This puts Neo on the internet at a real link your dad can bookmark — no
terminal, no Python, no setup on his end. He opens a URL, types the
username/password you give him, and he's in.

We use **Render**. The repo already contains the blueprint
([`render.yaml`](../render.yaml)) and the login gate, so this is mostly
clicking and pasting.

> **Before you start, have two things handy:**
> 1. Your filled **`neo.env`** values (the `NEO_*` keys).
> 2. A **username and password** you'll give your dad to log in — make these
>    up now (e.g. user `dad`, a strong password).

---

## 1. Create the Render service

1. Sign up at **https://render.com** (the free tier is fine to start).
2. **Connect GitHub:** Render will ask to access your repos — grant it access
   to **`mariahdi/neo`** (it's private, so this step is required).
3. Click **New → Blueprint**.
4. Pick the **`mariahdi/neo`** repo. Render reads `render.yaml` and shows a
   service called **neo-dashboard**.

## 2. Paste in the secrets

Render will prompt for every value marked `sync: false` in the blueprint.
Fill them in:

| Variable | What to paste |
|---|---|
| `DASHBOARD_USER` | the username for your dad (e.g. `dad`) |
| `DASHBOARD_PASS` | the password for your dad (make it strong) |
| `NEO_JIRA_BASE_URL` | from your `neo.env` |
| `NEO_JIRA_EMAIL` | from your `neo.env` |
| `NEO_JIRA_API_TOKEN` | from your `neo.env` |
| `NEO_ANTHROPIC_API_KEY` | from your `neo.env` |
| `NEO_GITHUB_TOKEN` | from your `neo.env` |
| `NEO_GITHUB_REPO` | `mariahdi/neo` |
| `NEO_JIRA_PROJECT` | `NEO` |

> These live only in Render's settings — they're never in the repo. Treat them
> like the `neo.env` file: private.

## 3. Deploy

Click **Apply / Create**. Render installs the dependencies and starts the app
(first build takes a few minutes). When it's live you'll get a URL like:

```
https://neo-dashboard-xxxx.onrender.com
```

Open it. Your browser will show a **Sign in** popup — enter the
`DASHBOARD_USER` / `DASHBOARD_PASS` you chose. The live dashboard loads.

## 4. Hand it to your dad

Send him three things:
- the **link** (`https://neo-dashboard-xxxx.onrender.com`),
- the **username**, and
- the **password**.

That's it — he opens the link, signs in once (the browser remembers it), and
bookmarks it. No `docs/SETUP.md` needed; that guide is only for running it on
his own Mac.

---

## Good to know

- **Cost / sleeping.** The blueprint uses the **free** plan, which spins the
  app down when idle, so the first visit after a quiet spell takes ~30 seconds
  to wake. For an always-instant link, switch the service to the **Starter**
  plan (~$7/month) — change `plan: free` to `plan: starter` in `render.yaml`,
  or pick the plan in the Render dashboard.
- **AI usage** bills to your `NEO_ANTHROPIC_API_KEY`, same as a local run.
- **Auto-deploys.** Every push to `main` redeploys automatically.
- **Session secret.** Set **`SESSION_SECRET`** (e.g. run `openssl rand -hex 32`
  and paste the result) so logins stay valid across restarts and can't be
  forged. Without it, the app warns and falls back to a key derived from the
  password (or a random key that resets each restart). Rotating it logs everyone
  out.
- **Changing the password / locking him out.** Edit `DASHBOARD_PASS` in the
  Render dashboard (Environment tab) and save — it restarts with the new
  password. Rotate it any time.
- **It still works locally.** Without `DASHBOARD_USER` / `DASHBOARD_PASS` set
  (i.e. your own `neo.env` runs) there's no password prompt, so
  `./run-dashboard.sh` is unchanged.

---

## Optional: make edited data durable

By default the module data (About text/photo, Stocks, Goals, Wins) lives in
JSON files inside the container, which Render **wipes on every redeploy**. Two
ways to keep it — **Option A (free Postgres) is recommended.**

### Option A — Free Postgres (recommended, no monthly cost)

1. Create a free Postgres database:
   - **Supabase** (supabase.com) → New project, or
   - **Neon** (neon.tech) → New project.
2. Copy its **connection string** (a `postgresql://user:password@host:5432/db`
   URI). In Supabase it's **Project Settings → Database → Connection string →
   URI**; in Neon it's shown on the project dashboard.
3. Render → your **neo-dashboard** service → **Environment** → add
   `DATABASE_URL` = that string → **Save** (it redeploys).

Done. The app creates a small `neo_store` table on first write and keeps
everything there, surviving redeploys — no code change, and you stay on the
free Render plan. (Heads-up: free databases may pause after a long idle stretch
and take a few seconds to wake on the next visit.)

### Option B — Render persistent disk (paid)

Keeps the JSON files on a mounted disk instead. Needs a **paid instance**
(~$7/mo Starter, which also makes the app always-on, so cold starts go away):

1. Render → your **neo-dashboard** service → **Settings** → set **Instance
   Type** to **Starter**.
2. **Settings → Disks → Add Disk:** Name `neo-data`, Mount Path `/var/data`,
   Size `1 GB`.
3. **Environment** → add `NEO_DATA_DIR` = `/var/data` → Save (it redeploys).

The app already reads `NEO_DATA_DIR`, so edits then survive redeploys. (If you
set both, `DATABASE_URL` wins.)

## Optional: automate the daily stock briefings (cron)

The Stocks page has a manual "Refresh" button; this runs it for every stock
once a day automatically. The job (`dashboard/jobs/refresh_stocks.py`) calls
the live app's API, so it needs no direct data access. Render **Cron Jobs are
a paid feature**.

1. Render → **New → Cron Job** → connect **`mariahdi/neo`**.
2. **Build command:** `pip install -r requirements.txt`
   **Command:** `python -m dashboard.jobs.refresh_stocks`
   **Schedule:** `0 13 * * *` (daily 13:00 UTC — adjust to taste).
3. **Environment** → add `NEO_APP_URL` (your `https://neo-dashboard-….onrender.com`),
   plus `DASHBOARD_USER` and `DASHBOARD_PASS` (the same login).
4. Create. It refreshes every stock's briefing each day; run it by hand from the
   service page any time to test.

> Heads-up: each run makes one Anthropic call per stock, so it bills a little
> daily. Real-time prices still need a market-data feed — this gives a daily
> AI-written briefing, not live quotes.
