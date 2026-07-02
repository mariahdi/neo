"""Module registry (NEO-37) — the catalog of optional modules.

One source of truth for what modules exist. Each instance enables a subset:
an `owner` profile (Aria) auto-gets everything the moment it ships; a `member`
(Neo / dad) keeps a curated set and opts into new ones from the in-app catalog.

Enablement + a `seen` marker persist per instance in the store, so opting in is
a data write — not a deploy. "Releasing" a module = adding it here and shipping;
members then see it as available, with a ✨ badge until they've looked.
"""
from __future__ import annotations

import os

from . import profile, store

# Each module: key, name, path, description, version, released (ISO date), and
# the integrations it needs to actually work.
# The 9 "Dashboards for Life" (Chuck's framing, 2026-07). Five reuse existing
# modules (renamed); four are new scaffolds in categories.py. The retired modules
# (Recipes, Stocks, Wins, Body, Wealth, Daily Bread) are archived — their code +
# routers still exist and work; they're just not in the catalog. To bring one
# back, re-add its dict here (originals in MODULES_ARCHIVE.md) + list it in the
# profile's "modules". Order below = the order tiles appear in the launcher.
MODULES = [
    {"key": "wellness", "icon": "🌿", "name": "Health & Wellness", "path": "/wellness",
     "description": "Body, mind, and daily rhythm — non-negotiables, routine, and life rules.",
     "version": "1.0", "released": "2026-06-17", "requires": []},
    {"key": "nominal", "icon": "💰", "name": "Finance & Wealth", "path": "/nominal",
     "description": "Budget by Fixed / Loose / Float / Savings, with audience masking.",
     "version": "1.0", "released": "2026-06-17", "requires": []},
    {"key": "goals", "icon": "⏱️", "name": "Time & Habits", "path": "/goals",
     "description": "Goals and habits that work for you — natural-language updates.",
     "version": "1.0", "released": "2026-06-16", "requires": ["anthropic"]},
    {"key": "career", "icon": "📈", "name": "Career & Business Growth", "path": "/career",
     "description": "Applications, milestones, prep notes, and a to-do checklist.",
     "version": "1.0", "released": "2026-06-18", "requires": []},
    {"key": "relationships", "icon": "🤝", "name": "Relationships & Connection", "path": "/relationships",
     "description": "The people who matter — remembered and appreciated.",
     "version": "0.1", "released": "2026-07-02", "requires": []},
    {"key": "growth", "icon": "📚", "name": "Personal Growth & Learning", "path": "/growth",
     "description": "Learning, curiosity, and becoming — on your timeline.",
     "version": "0.1", "released": "2026-07-02", "requires": []},
    {"key": "vision", "icon": "✨", "name": "Vision Board & Purpose", "path": "/vision",
     "description": "What you're building toward — clear and alive.",
     "version": "0.1", "released": "2026-07-02", "requires": []},
    {"key": "trips", "icon": "🌴", "name": "Recreation, Fun & Travel", "path": "/trips",
     "description": "Trips, rest days, and hobby time — memories kept, joy protected.",
     "version": "1.0", "released": "2026-06-17", "requires": []},
    {"key": "legacy", "icon": "🕊️", "name": "Legacy & Contribution", "path": "/legacy",
     "description": "The mark you leave — giving, mentorship, and legacy goals.",
     "version": "0.1", "released": "2026-07-02", "requires": []},
    {"key": "about", "icon": "✦", "name": "About", "path": "/about",
     "description": "The story of how this was built.",
     "version": "1.0", "released": "2026-06-16", "requires": [], "hidden": True},

    # Retired from the Aria product (not on the demo/default profiles), but kept
    # registered + hidden so other instances still work — Nessa's Recipes, Chuck's
    # Daily Bread, etc. To bring one onto the Aria dashboard, add its key to the
    # profile's "modules" list. Code + routers for all of these are still mounted.
    {"key": "recipes", "icon": "🍴", "name": "Recipes", "path": "/recipes",
     "description": "Save your favorite recipes — bookmark any from the web with a tap.",
     "version": "1.0", "released": "2026-06-27", "requires": [], "hidden": True},
    {"key": "stocks", "icon": "📈", "name": "Stocks", "path": "/stocks",
     "description": "Sector watchlist with daily AI briefings.",
     "version": "1.0", "released": "2026-06-16", "requires": ["anthropic"], "hidden": True},
    {"key": "wins", "icon": "🌟", "name": "Wins", "path": "/wins",
     "description": "Daily wins with AI recognition.",
     "version": "1.0", "released": "2026-06-16", "requires": ["anthropic"], "hidden": True},
    {"key": "body", "icon": "🫀", "name": "Body", "path": "/body",
     "description": "Meds, weight journey, and habits — private by default.",
     "version": "1.0", "released": "2026-06-17", "requires": [], "hidden": True},
    {"key": "wealth", "icon": "📊", "name": "Wealth", "path": "/wealth",
     "description": "Investments + retirement projections, with audience masking.",
     "version": "1.0", "released": "2026-06-17", "requires": [], "hidden": True},
    {"key": "dailybread", "icon": "🕊️", "name": "Daily Bread", "path": "/daily-bread",
     "description": "A daily verse, a family photo wall, and a prayer list.",
     "version": "1.0", "released": "2026-06-21", "requires": [], "hidden": True},
]
_BY_KEY = {m["key"]: m for m in MODULES}
ALL_KEYS = [m["key"] for m in MODULES]


def is_owner() -> bool:
    return profile.ACTIVE.get("role") == "owner"


def _state() -> dict:
    """The member's enabled set + seen marker (persisted). Owner ignores it."""
    default = {"enabled": list(profile.ACTIVE.get("modules", ALL_KEYS)), "seen": None}
    st = store.load("modules", default)
    st.setdefault("enabled", default["enabled"])
    st.setdefault("seen", None)
    return st


def enabled_keys() -> list[str]:
    """Keys this instance shows, in registry order. Owner = everything except
    `hidden` (opt-in-only) modules, unless the profile explicitly lists them."""
    if is_owner():
        explicit = set(profile.ACTIVE.get("modules", []))
        return [k for k in ALL_KEYS if not _BY_KEY[k].get("hidden") or k in explicit]
    on = set(_state()["enabled"])
    return [k for k in ALL_KEYS if k in on]


def enabled_modules() -> list[dict]:
    on = set(enabled_keys())
    return [m for m in MODULES if m["key"] in on]


def integrations_present() -> set[str]:
    present = set()
    if os.environ.get("NEO_ANTHROPIC_API_KEY"):
        present.add("anthropic")
    if os.environ.get("NEO_JIRA_API_TOKEN"):
        present.add("jira")
    if os.environ.get("NEO_GITHUB_TOKEN"):
        present.add("github")
    return present


def available_modules() -> list[dict]:
    """Modules not yet enabled, flagged `isNew` (released since last seen) and
    with any `unmet` integration requirements for this instance."""
    on = set(enabled_keys())
    seen = _state().get("seen")
    present = integrations_present()
    out = []
    for m in MODULES:
        if m["key"] in on or m.get("hidden"):
            continue  # hidden = opt-in only; never advertised in the catalog
        is_new = seen is None or m["released"] > seen
        unmet = [r for r in m.get("requires", []) if r not in present]
        out.append({**m, "isNew": is_new, "unmet": unmet})
    return out


def new_count() -> int:
    return sum(1 for m in available_modules() if m["isNew"])


def enable(key: str) -> None:
    if key not in _BY_KEY or is_owner():
        return
    st = _state()
    if key not in st["enabled"]:
        st["enabled"].append(key)
        store.save("modules", st)


def disable(key: str) -> None:
    """Member turns a module off (owner keeps everything; no-op for owner)."""
    if key not in _BY_KEY or is_owner():
        return
    st = _state()
    if key in st["enabled"]:
        st["enabled"] = [k for k in st["enabled"] if k != key]
        store.save("modules", st)


def reset_modules() -> None:
    """Reset which modules are shown back to the profile default. Module DATA
    (recipes, about, etc.) is untouched — this only rewrites the enabled set."""
    if is_owner():
        return
    st = _state()
    store.save("modules", {"enabled": list(profile.ACTIVE.get("modules", ALL_KEYS)),
                           "seen": st.get("seen")})


def mark_seen(when: str) -> None:
    if is_owner():
        return
    st = _state()
    st["seen"] = when
    store.save("modules", st)
