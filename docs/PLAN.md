# Neo — Planning & Architecture

> A personal operating system for getting work done by voice. You say what you want; Neo routes it, drafts it, gets it reviewed by a human, and reports back when it's done.

**Status:** Planning / pre-MVP
**Proof of concept:** Proposals module
**Driving constraint:** Ship something usable before Dad's shoulder surgery, so he can stay productive from bed.

---

## 1. What Neo is

Neo is the orchestration layer of a life/work automation system. The owner (initially Dad — former SVP at an IT consulting firm) speaks a request. Neo turns that into a tracked unit of work, hands it to Claude to draft, opens it for a human expert to review, and surfaces it back to the owner for final sign-off.

The design principle borrowed from flight software (GNC): a clean **main loop** plus a **sequencer**, with discrete modules that execute only when they've been "checked out." Same discipline applied to life admin instead of a satellite.

Two things stay rigorously separated:

- **The infrastructure** (Neo loop, module scaffolding, workflow logic) — shareable, open, generic.
- **The substance** (Dad's proposals, templates, pricing, client data, account info) — private, never committed to a public repo.

This is the same pattern as the "work brag book": the structure is public and reusable, the contents are personal and live in a separate data file.

---

## 2. Core architecture

### 2.1 The Neo loop (orchestrator)

The central repo (`neo`) is the main loop. It does **routing and orchestration only**:

- Receives input (voice → structured request).
- Decides which module the request belongs to.
- Loads the right skill from the personal data layer.
- Tracks state across Jira and GitHub.
- Surfaces status back to the owner.

It deliberately does **not** hold sensitive data itself. Sensitive modules (e.g. banking) stay self-contained and report back only what's necessary — "task complete," not the underlying account details. Smaller attack surface, data stays compartmentalized.

### 2.2 Modules as checked-out sub-repos

Modules live as separate repositories, cloned in on demand — like `git clone`-ing only the piece you need. You configure Neo, run it through a "compiler"/loader step that pulls the sub-repos you've enabled, and you only carry what you use. Lighter footprint, faster, and each module is independently versioned.

Module roadmap (proposals first, then scale):

1. **Proposals** ← proof of concept
2. Landlord responsibilities
3. Air Force website development
4. Mental health app
5. Finance / stocks / tech

### 2.3 The personal data layer

A private store (separate config / JSON, never committed publicly) holding everything specific to the owner:

- Past proposals, templates, brand voice, company guidelines
- Pricing models and methodologies
- Skills (see below)
- Anything client-sensitive

Neo references this layer at runtime but never exposes it. The public infra + private data split is what makes Neo shareable: someone else could clone Neo and drop in their *own* data layer.

### 2.4 Skills + skill loader

Skills are modular capabilities (e.g. *nonprofit proposal*, *government contract proposal*, *tech project proposal*). They live in the **personal data layer** for privacy, but Neo has a **skill loader** that knows how to fetch and apply them.

Flow: Dad says "American Red Cross proposal" → Neo recognizes a proposal task → skill loader pulls the *nonprofit proposal* skill from the private layer → passes it to Claude as context alongside the voice input. The skill itself never leaves the private layer or hits GitHub.

Skill selection can be **inferred** ("Red Cross" → nonprofit) or **explicit override** ("use the government contracts skill").

---

## 3. The proposal workflow (end to end)

This is the proof of concept. Everything else is a variation on this spine.

```
Dad's brain (voice)
      │
      ▼
  Jira ticket  (PROP-N)  ── prompts + context captured from speech
      │
      ▼
  Categorization ── hot? / time estimate / start = yes|no
      │
      ├── HOT  ───────────► Claude auto-starts
      └── STANDARD / LOW ─► queued until Dad triggers or asks "what can I do in 5 min?"
      │
      ▼
  Claude (acting as a "developer")
   - checks out branch  feature/PROP-N
   - loads the right skill from personal data layer
   - drafts the proposal (lives IN the repo, so reviewers can comment inline)
   - commits, pushes, opens a Pull Request
      │
      ▼
  Notification to reviewer  (per contract: on-call in business hours / ping for hot / dashboard)
      │
      ▼
  Human developer review
   - reviews PR, comments on specific sections
   - if changes needed → sub-prompts / additional skills → Claude revises
   - signs off
      │
      ▼
  Dad's final review
   - Approve  → ticket → DONE, PR merged
   - Reject   → ticket → back to IN PROGRESS
```

### Jira state model

```
[Dad's brain] → To Do → In Progress → In Review → Done
                            ▲                          │
                            └──── (Dad rejects) ───────┘
```

### Key decisions locked in

| Question | Decision |
|---|---|
| How much input does Claude need to start? | Minimal. Dad speaks in "prompt-style"; Claude drafts from whatever context is given + the loaded skill. |
| Auto-start or manual trigger? | **Both.** Hot items auto-start; standard/low queue until Dad explicitly starts them or asks what fits a time window. |
| Where does the proposal text live? | **In the repo** — so reviewers can comment on actual content inline. Privacy handled via repo permissions (only contracted developers have access). |
| How do reviewers get notified? | Flexible per contract: on-call during business hours, ping for hot items, or a dashboard they check. |
| Where do skills live? | In the **personal data layer** (private); Neo's skill loader fetches and applies them. |
| Does Claude/the system expose Git to reviewers? | **No.** See abstraction layer below. |

---

## 4. Branch + ticket convention

- Ticket: `PROP-1`, `PROP-2`, …
- Branch: `feature/PROP-1` (one feature branch per ticket)
- Claude opens the PR; GitHub tracks the branch, commits, and PR; Jira tracks the feature/status.

GitHub and Jira together give a full audit trail: *Claude opened branch X, made these commits, requested this PR; ticket moved To Do → In Progress → In Review → Done.* Dad can see a proposal was verified by both AI and a human before he signed off.

---

## 5. The abstraction (UI) layer

Not every contributor is technical. A proposals reviewer shouldn't have to navigate Git or even Jira. So Neo gets a UI layer (its own sub-repo) that hides the plumbing:

- Reviewer logs into a simple app → sees their tasks → comments / approves / rejects.
- Behind the scenes Neo handles branch checkouts, commits, PRs, ticket transitions.
- Different roles/domains get interfaces matched to how those people actually work. A code-change task triggers the right "hat" — *"we have our proposals hat on, here are the questions to ask, this is what triggers a commit/push."*

Mariah (technical) is comfortable in GitHub directly; the UI exists for everyone who isn't.

---

## 6. The "what can I do in 5 minutes?" interaction

Tasks carry a category + time estimate. Dad can say *"I have five minutes, what can I work on?"* → Claude scans open tickets → returns matches (e.g. "PROP-1 and TESLA-2 each fit five minutes") → Dad picks one → Claude opens the ticket, explains what it does and how it proposes to handle it. This mirrors a tiered data-annotation queue: items are categorized, prioritized, and matched to who's qualified/available.

---

## 7. Context & people

- **Mariah** — GNC engineer at Umbra (satellites/flight software). Building this. Prior work: `nominalmoney.netlify.app` (budgeting app) and the "work brag book" (public structure / private data JSON — the model for Neo's data separation).
- **Dad** — owner/primary user; former SVP at a small–midsize IT consulting firm. Knows client relationships, scoping, and proposals cold. Neo automates the grunt work so he can stay on strategy and relationships — including from bed post-surgery.
- **Reviewers** — contracted developers with varying expertise tiers (proposals, etc.) and varying availability. *Open question: Dad likely already has specific people in mind — confirm who, since it shapes the UI requirements.*

---

## 8. Open questions / next steps

1. **Reviewer list** — who are the actual proposal reviewers, and what does their interface need to do? (Ask Dad.)
2. **Start trigger mechanics** — webhook on ticket creation vs. polling Jira. (Implementation detail; webhook likely cleaner for hot-item auto-start.)
3. **Personal data layer shape** — single config file vs. a queryable knowledge base for templates/past proposals.
4. **Repo scaffolding** — lay down the Neo skeleton (loop, module loader, docs) before filling in the proposal module.
5. **Seed Jira** — create the first PROP tickets and the workflow columns to match the state model above.
