"""
Demo data for the Neo web app.

Used only when the integration credentials (NEO_JIRA_* / NEO_ANTHROPIC_* /
NEO_GITHUB_*) are NOT set. It lets the dashboard, review queue, and proposal
screens render with realistic sample content so the app can be shown end to
end without touching live Jira, GitHub, or Claude. The moment real keys are
present, every API switches back to live data and this module is never used.

Nothing here makes a network call. Editing a proposal below changes what the
demo shows — it's the data file for "demo mode."
"""

# Each proposal carries every field the reviewer screens read:
#   id, title, sender, amount, deadline (friendly), deadline_iso (for the
#   dashboard formatter), funder, category, summary, draft, column.
# `column` places it on the dashboard board: queued | drafting | review | done.
DEMO_PROPOSALS = [
    {
        "id": "NEO-2",
        "column": "review",
        "title": "American Red Cross — Disaster Relief Grant",
        "sender": "American Red Cross",
        "amount": "$2,500,000",
        "deadline": "Sep 15, 2026",
        "deadline_iso": "2026-09-15",
        "funder": "FEMA",
        "category": "HOT",
        "summary": "Funding for mobile disaster-relief shelters across the Gulf Coast.",
        "draft": (
            "Dear American Red Cross Grants Committee,\n\n"
            "We are honored to submit this proposal for a $2,500,000 disaster-relief "
            "grant to fund the deployment of mobile shelters across the Gulf Coast "
            "region. Recent hurricane seasons have shown that the window between a "
            "storm's landfall and the arrival of safe shelter is the single greatest "
            "predictor of displacement-related harm.\n\n"
            "Our program places forty rapid-deploy shelter units in three staging "
            "hubs — Houston, New Orleans, and Mobile — each able to reach an affected "
            "community within six hours. Year one funds the units and logistics; year "
            "two funds staffing, maintenance, and a regional coordination center.\n\n"
            "We respectfully request your partnership in making the Gulf Coast more "
            "resilient, one shelter at a time.\n\n"
            "With gratitude,\nThe Proposals Team"
        ),
    },
    {
        "id": "NEO-5",
        "column": "review",
        "title": "Habitat for Humanity — Rebuild Initiative",
        "sender": "Habitat for Humanity",
        "amount": "$640,000",
        "deadline": "Oct 30, 2026",
        "deadline_iso": "2026-10-30",
        "funder": "HUD Community Block Grant",
        "category": "STD",
        "summary": "Rebuilding twelve homes for families displaced by spring flooding.",
        "draft": (
            "Dear Habitat for Humanity Review Board,\n\n"
            "This proposal requests $640,000 to rebuild twelve homes for families "
            "displaced by this spring's flooding. Each rebuild follows our "
            "volunteer-led model, pairing a sponsored family with a build crew and a "
            "long-term affordability covenant.\n\n"
            "Funds cover materials, site preparation, and a part-time construction "
            "lead for the eighteen-month build window. Families contribute sweat "
            "equity and enter homeownership with a zero-interest mortgage.\n\n"
            "Thank you for considering this investment in stable, affordable housing.\n\n"
            "Sincerely,\nThe Proposals Team"
        ),
    },
    {
        "id": "NEO-7",
        "column": "drafting",
        "title": "City Food Bank — Cold Storage Expansion",
        "sender": "City Food Bank",
        "amount": "$310,000",
        "deadline": "Nov 12, 2026",
        "deadline_iso": "2026-11-12",
        "funder": "State Hunger Relief Fund",
        "category": "STD",
        "summary": "Doubling refrigerated capacity to accept fresh-produce donations.",
        "draft": (
            "Dear City Food Bank Board,\n\n"
            "We propose a $310,000 cold-storage expansion that would double the food "
            "bank's refrigerated capacity, unlocking acceptance of large fresh-produce "
            "donations currently turned away for lack of space.\n\n"
            "(Draft in progress — Neo is still writing this one.)"
        ),
    },
    {
        "id": "NEO-9",
        "column": "queued",
        "title": "Boys & Girls Club — After-School STEM",
        "sender": "Boys & Girls Club",
        "amount": "$185,000",
        "deadline": "Jan 20, 2027",
        "deadline_iso": "2027-01-20",
        "funder": "Regional Education Foundation",
        "category": "STD",
        "summary": "An after-school STEM lab for 200 students in underserved districts.",
        "draft": "(Not drafted yet — waiting in the queue for Neo to pick it up.)",
    },
    {
        "id": "NEO-3",
        "column": "done",
        "title": "Veterans Outreach — Transitional Housing",
        "sender": "Veterans Outreach Coalition",
        "amount": "$1,150,000",
        "deadline": "Aug 1, 2026",
        "deadline_iso": "2026-08-01",
        "funder": "VA Supportive Services",
        "category": "HOT",
        "summary": "Transitional housing and job placement for 80 returning veterans.",
        "draft": (
            "Dear Veterans Outreach Coalition,\n\n"
            "This approved proposal funds transitional housing and job-placement "
            "services for eighty returning veterans over a two-year period.\n\n"
            "Approved and parked for owner sign-off.\n\n"
            "Respectfully,\nThe Proposals Team"
        ),
    },
]

_BY_ID = {p["id"]: p for p in DEMO_PROPOSALS}

# Mirrors dashboard_api.COLUMNS (kept here to avoid a circular import).
_COLUMNS = [
    {"key": "queued",   "label": "Queued",      "blurb": "Just requested — waiting for Neo."},
    {"key": "drafting", "label": "Drafting",    "blurb": "Neo is drafting it."},
    {"key": "review",   "label": "Needs Review", "blurb": "Ready for your sign-off."},
    {"key": "done",     "label": "Approved",    "blurb": "Signed off and parked."},
]


def _public(p: dict) -> dict:
    """Return a copy without internal-only keys (column, deadline_iso)."""
    return {k: v for k, v in p.items() if k not in ("column", "deadline_iso")}


def demo_review_queue() -> list[dict]:
    """Proposals currently in review, in the reviewer-facing shape."""
    return [_public(p) for p in DEMO_PROPOSALS if p["column"] == "review"]


def demo_get_proposal(proposal_id: str) -> dict | None:
    """One proposal by id, or None if there's no such demo proposal."""
    p = _BY_ID.get(proposal_id)
    return _public(p) if p else None


def demo_dashboard() -> dict:
    """The control-panel board, matching dashboard_api.get_dashboard()'s shape."""
    buckets = {c["key"]: [] for c in _COLUMNS}
    for p in DEMO_PROPOSALS:
        buckets[p["column"]].append({
            "id": p["id"],
            "title": p["title"],
            "deadline": p["deadline_iso"],   # dashboard formats ISO -> friendly
            "category": p["category"],
        })
    columns = [{
        "key": c["key"],
        "label": c["label"],
        "blurb": c["blurb"],
        "count": len(buckets[c["key"]]),
        "items": buckets[c["key"]],
    } for c in _COLUMNS]
    return {"total": len(DEMO_PROPOSALS), "columns": columns}
