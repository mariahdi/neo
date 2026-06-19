# Neo

> A personal operating system for getting work done by voice. Say what you
> want; Neo routes it, drafts it with AI, gets it reviewed by a human, and
> reports back for your sign-off.

**Status:** working app · proposals + USAFA web-dev on the live loop, plus a
suite of personal modules · runs as multiple themed instances via profiles (no fork)

The full write-up is in [`docs/PLAN.md`](docs/PLAN.md). A screen-shareable
walkthrough lives in [`docs/plan-site/`](docs/plan-site/) (open `index.html`).

**Setting it up for a non-technical reviewer?** See the plain-English
[`docs/SETUP.md`](docs/SETUP.md) to run it on their Mac, or
[`docs/DEPLOY.md`](docs/DEPLOY.md) to host it (Render) so they just open a
password-protected link — no terminal at all.

**Want your own personalized instance?** One codebase runs many instances via
profiles (own theme, login, data, modules) — no fork. See [`docs/ARIA.md`](docs/ARIA.md).

## The dashboard

The everyday surface is a personalized web app (FastAPI, server-rendered) that
one codebase serves as many **instances** via profiles — each with its own
theme, identity, login, data, and module set. No fork.

A chat bar (**Ask Neo**, type or speak) routes a request by intent — log a win,
update a goal, or open a ticket and draft it on the live loop.

**Work surfaces** — the Jira-driven side, split by type so each has its own home:

- **USAFA** — a request bar + a USAFA-only board for Air Force Academy web-dev
  tasks, with its own sign-off queue.
- **Proposals** — the proposal-drafting board plus the **Approve / Request
  Changes / Re-prompt** review queue.
- **Dev** — the app's own build / maintenance tickets.

**Personal modules** — each ships blank, edits inline, and persists to the
store: About, Stocks (live prices + AI briefings + 30-day sparklines), Goals,
Wins, Nominal (budget), Body, Wealth, Trips, Wellness, Career. New modules show
up in an in-app catalog — the owner instance auto-gets them; members opt in.

```bash
pip3 install -r requirements.txt        # one-time
source neo.env && ./run-dashboard.sh    # → http://127.0.0.1:8000
```

With no `NEO_*` keys set it runs in **demo mode** (sample data); set the Jira /
GitHub / Anthropic keys to go live. Data persists to JSON files by default, or
set `DATABASE_URL` (Postgres) for storage that survives redeploys, with a local
file cache as a fallback. The dashboard reuses the same loop the CLI runs — see
"Try the loop" and "Going live" below, and [`docs/ARIA.md`](docs/ARIA.md) for
profiles + deployment.

## The shape

```
neo/
├── neo/                 # the main loop + sequencer (orchestration only)
│   ├── loop.py          # the control loop, modeled on flight software
│   ├── router.py        # request -> module + skill
│   ├── skill_loader.py  # pulls skills from the PRIVATE data layer
│   ├── integrations.py  # Jira / GitHub / Claude seams (live + dry)
│   ├── module.py        # the contract every module implements
│   └── neo_types.py     # WorkItem + the state model
├── modules/
│   ├── proposals/       # the proof-of-concept module
│   └── usafa/           # Air Force Academy web-dev module
├── dashboard/           # the personalized web app (work surfaces + modules)
│   ├── main.py          # FastAPI app: the Proposals page + home routing
│   ├── work.py          # USAFA + Dev surfaces (filtered boards, sign-off)
│   ├── chat.py          # "Ask Neo" — intent routing -> ticket -> draft
│   ├── profile.py       # active instance profile (theme/identity/nav/home)
│   ├── profiles/        # neo.json, aria.json — per-instance config
│   ├── registry.py      # module catalog (owner auto-enables; members opt in)
│   ├── store.py         # key/value store: JSON files or Postgres + cache
│   ├── auth.py          # session login (when DASHBOARD_USER/PASS set)
│   ├── theme.py         # shared nav + page shell, themed per profile
│   └── about.py · stocks.py · goals.py · wins.py · nominal.py · body.py
│       · wealth.py · trips.py · wellness.py · career.py   # the modules
├── reviewer/            # backend read/write APIs the dashboard reuses
│   ├── dashboard_api.py # the board (read) + create a request
│   ├── review_api.py    # In Review proposals + drafts (read)
│   └── actions_api.py   # approve / request changes / re-prompt (write)
├── personal-data/       # PRIVATE, gitignored — templates, skills, client data
├── config/              # neo.config.example.json
└── docs/                # PLAN.md, SETUP.md + the plan site
```

Two things stay strictly apart: the **infrastructure** (this repo, shareable)
and the **substance** (everything in `personal-data/`, private). Neo reads
from the data layer but never exposes it.

## Try the loop (no integrations needed)

```bash
python -m neo --dry-run
```

This narrates the proposals loop on the same NEO-2 example that's on the
Jira board — hot item auto-starts, router picks the module, the nonprofit
skill loads, Claude drafts, a branch + PR are opened, the ticket moves to
In Review. Add `--force-start` to also run the queued (non-hot) item.

## Going live

1. `cp config/neo.config.example.json config/neo.config.json` and edit.
2. In `personal-data/`, copy the `*.example.*` stubs to real files and fill
   them in (they're gitignored).
3. Set the integration env vars (Jira, GitHub, Anthropic) and run
   `python -m neo --live`. See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

## Workflow

```
Speak -> Sort -> Draft (Claude) -> Review (human) -> Approve (owner)

State: to_do -> in_progress -> in_review -> done
                    ^                          |
                    +------ (owner rejects) ---+
```

One feature branch per ticket: `feature/NEO-2`.
