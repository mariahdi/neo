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
- **Changing the password / locking him out.** Edit `DASHBOARD_PASS` in the
  Render dashboard (Environment tab) and save — it restarts with the new
  password. Rotate it any time.
- **It still works locally.** Without `DASHBOARD_USER` / `DASHBOARD_PASS` set
  (i.e. your own `neo.env` runs) there's no password prompt, so
  `./run-dashboard.sh` is unchanged.
