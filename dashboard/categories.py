"""The new "Dashboards for Life" categories that don't have a full module yet.

Chuck's 9-category framing (2026-07): four categories don't map to an existing
module, so they ship here as scaffolded "coming soon" dashboards — real routes
in the catalog that we build up over time. The other five categories reuse
existing modules (renamed in registry.py): Health & Wellness (wellness),
Finance & Wealth (nominal), Time & Habits (goals), Career & Business Growth
(career), Recreation Fun & Travel (trips).
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from . import theme

router = APIRouter()

# key -> display. `coming` = the widgets we plan to build for that dashboard.
CATEGORIES = {
    "relationships": {
        "icon": "🤝", "name": "Relationships & Connection",
        "tag": "The people who matter — remembered and appreciated.",
        "coming": [
            "Contact cadence — a nudge for who you haven't talked to in a while",
            "Important dates and how you like to show up for people",
            "A connection board for the relationships you're nurturing",
        ],
    },
    "growth": {
        "icon": "📚", "name": "Personal Growth & Learning",
        "tag": "Learning, curiosity, and becoming — on your timeline.",
        "coming": [
            "Books and courses in progress",
            "Reflections and journal prompts",
            "Skills you're building, and where you're headed",
        ],
    },
    "vision": {
        "icon": "✨", "name": "Vision Board & Purpose",
        "tag": "What you're building toward — clear and alive.",
        "coming": [
            "A living vision board of what you want",
            "Values and purpose reflections",
            "A values-vs-actions alignment view",
        ],
    },
    "legacy": {
        "icon": "🕊️", "name": "Legacy & Contribution",
        "tag": "The mark you leave — tracked with intention.",
        "coming": [
            "A giving and volunteering log",
            "Mentorship and family-legacy goals",
            "Contribution milestones over time",
        ],
    },
}

_CSS = """
<style>
  .cs-wrap{max-width:720px;margin:6px auto;}
  .cs-hero{text-align:center;padding:26px 20px 30px;}
  .cs-ic{font-size:60px;line-height:1;display:block;margin-bottom:14px;}
  .cs-hero h1{font-size:38px;margin-bottom:8px;}
  .cs-hero p{color:var(--muted);font-size:15px;max-width:460px;margin:0 auto 18px;line-height:1.6;}
  .cs-badge{display:inline-block;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:var(--gold);
    border:1px solid var(--gold-line);border-radius:20px;padding:5px 14px;}
  .cs-sub{font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:var(--muted);margin:14px 0 12px;}
  .cs-grid{display:grid;gap:12px;}
  .cs-card{background:var(--panel);border:1px solid var(--line-soft);border-radius:14px;padding:18px 20px;
    color:var(--text);font-size:14.5px;line-height:1.5;display:flex;gap:12px;align-items:flex-start;}
  .cs-card::before{content:"✦";color:var(--gold);flex-shrink:0;}
</style>
"""


def _page(key: str) -> HTMLResponse:
    c = CATEGORIES[key]
    cards = "".join(f'<div class="cs-card">{item}</div>' for item in c["coming"])
    body = f"""{_CSS}
<main class="cs-wrap">
  <div class="cs-hero">
    <span class="cs-ic">{c['icon']}</span>
    <h1>{c['name']}</h1>
    <p>{c['tag']}</p>
    <span class="cs-badge">&#10022; Coming soon</span>
  </div>
  <div class="cs-sub">What this dashboard will hold</div>
  <div class="cs-grid">{cards}</div>
</main>
"""
    return HTMLResponse(theme.page(c["name"], body, active=key))


@router.get("/relationships", response_class=HTMLResponse)
async def relationships_page() -> HTMLResponse:
    return _page("relationships")


@router.get("/growth", response_class=HTMLResponse)
async def growth_page() -> HTMLResponse:
    return _page("growth")


@router.get("/vision", response_class=HTMLResponse)
async def vision_page() -> HTMLResponse:
    return _page("vision")


@router.get("/legacy", response_class=HTMLResponse)
async def legacy_page() -> HTMLResponse:
    return _page("legacy")
