# Aria — your own instance

Aria is **not a fork**. It's the same codebase running as a different
*instance*: a profile picks the name, theme, and identity; a role decides what's
auto-on; data and login are its own. Any dev you do improves every instance —
Neo (dad's) and Aria (yours) — because the engine is shared and only the
*profile* differs.

```
            one repo (engine + every module)
                       │
        ┌──────────────┴──────────────┐
   NEO_PROFILE=neo              NEO_PROFILE=aria
   profiles/neo.json            profiles/aria.json
   role: member                 role: owner
   dad's login + DB             your login + DB
   navy/gold theme              warm "Her" theme
```

---

## How the pieces fit

| Concept | Where it lives | What it does |
|---|---|---|
| **Profile** | `profiles/<name>.json` | name, wordmark, `who`, tagline, **role**, theme `tokens` (colors + fonts), member's default `modules` |
| **Active profile** | `NEO_PROFILE` env (default `neo`) | selects which JSON loads; `profile.py` resolves it once |
| **Theme** | `theme.py` reads the profile tokens | every color/font is a CSS var from the profile — no per-module styling |
| **Registry** | `registry.py` | the catalog of all modules (`key, name, path, description, version, released, requires`) |
| **Role** | profile `role` | `owner` auto-enables every module; `member` keeps a curated set + opts in |
| **Catalog** | `/modules` + nav badge | members see ✨ new modules and enable them (a store write — no deploy) |
| **View-modes** | `theme.VIEW_JS` + a header badge | Private / Friends / Coworker / Public masking, opt-in per value |
| **Storage** | `store.py` | JSON files by default; **Postgres** when `DATABASE_URL` is set (per instance) |

### Roles
- **owner** (Aria) — every module is on the moment it ships; no catalog prompts.
- **member** (Neo / dad) — a curated set (`profile.modules`), plus a `/modules`
  catalog with a badge for anything released since they last looked. Opting in
  persists to *their* store, so it survives without a deploy.

### View-modes (privacy masking)
A header badge cycles **🔒 Private → 👥 Friends → 💼 Coworker → 🌍 Public**
(saved in your browser). A module opts a value in by rendering it as:

```html
<span class="mask" data-real="3200" data-avg="2200" data-type="currency">$3,200</span>
```

and calling `window.neoMaskScan()` after it (re)renders. The engine shows the
real value (private), the average/rounded value (friends/public), `—`
(coworker), or playful "monopoly money" (public + currency). Wrap a whole block
in `data-views="private"` to hide it outside chosen views. *Nominal* and *Body*
are the reference consumers.

---

## Launch Aria (one-time, ~15 min)

Aria is a **second Render service** off the same repo, with its own profile,
login, and database. Everything except the Render clicks is already in the repo.

> Have ready: a strong **username + password** for Aria, and (for Stocks/Goals/
> Wins) an **Anthropic API key**.

### 1. A database for Aria (free, durable)
Create a free Postgres at **Supabase** or **Neon**, copy its
`postgresql://…` connection string. (Skip only if you don't mind data resetting
on redeploy — then leave `DATABASE_URL` unset.)

### 2. The Render service
Render → **New → Web Service** → repo **`mariahdi/neo`**. Set:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn dashboard.main:app --host 0.0.0.0 --port $PORT`

**Environment:**

| Variable | Value |
|---|---|
| `NEO_PROFILE` | `aria` |
| `DASHBOARD_USER` | your login username |
| `DASHBOARD_PASS` | your login password |
| `SESSION_SECRET` | any long random string |
| `DATABASE_URL` | the Postgres URI from step 1 |
| `NEO_ANTHROPIC_API_KEY` | your Anthropic key (powers Stocks/Goals/Wins) |

(Aria doesn't need the Jira/GitHub keys unless you want the work-board modules.)

### 3. Open it
Deploy → open the new `https://…onrender.com` → sign in. You'll land in your
warm Aria OS, with its own login and data — completely separate from Neo.

---

## Make Aria yours

- **Re-skin:** edit the `tokens` (colors) and `font-head`/`font-body` in
  [`profiles/aria.json`](../dashboard/profiles/aria.json). All modules restyle.
- **Add a module:** build it like the others, add a row to `registry.MODULES`,
  and add it to `theme.NAV_LINKS`. Aria (owner) gets it instantly; dad gets a
  catalog nudge.
- **Make something private:** wrap values in `mask` spans / `data-views`
  blocks (see above).
- **Another person later:** drop a `profiles/<name>.json`, deploy a service with
  `NEO_PROFILE=<name>`. No fork, ever.
