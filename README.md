# Neo

> A personal operating system for getting work done by voice. Say what you
> want; Neo routes it, drafts it with AI, gets it reviewed by a human, and
> reports back for your sign-off.

**Status:** pre-MVP scaffold · **Proof of concept:** proposals module

The full write-up is in [`docs/PLAN.md`](docs/PLAN.md). A screen-shareable
walkthrough lives in [`docs/plan-site/`](docs/plan-site/) (open `index.html`).

## The shape

```
neo/
├── neo/                 # the main loop + sequencer (orchestration only)
│   ├── loop.py          # the control loop, modeled on flight software
│   ├── router.py        # request -> module + skill
│   ├── skill_loader.py  # pulls skills from the PRIVATE data layer
│   ├── integrations.py  # Jira / GitHub / Claude seams (stubbed)
│   ├── module.py        # the contract every module implements
│   └── types.py         # WorkItem + the state model
├── modules/
│   └── proposals/       # the proof-of-concept module
├── personal-data/       # PRIVATE, gitignored — templates, skills, client data
├── config/              # neo.config.example.json
└── docs/                # PLAN.md + the plan site
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
