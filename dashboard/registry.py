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
MODULES = [
    {"key": "about", "icon": "✦", "name": "About", "path": "/about",
     "description": "The story of how this was built.",
     "version": "1.0", "released": "2026-06-16", "requires": []},
    {"key": "recipes", "icon": "🍴", "name": "Recipes", "path": "/recipes",
     "description": "Gentle, gut-friendly recipes to browse and save.",
     "version": "1.0", "released": "2026-06-27", "requires": []},
    {"key": "stocks", "icon": "📈", "name": "Stocks", "path": "/stocks",
     "description": "Sector watchlist with daily AI briefings.",
     "version": "1.0", "released": "2026-06-16", "requires": ["anthropic"]},
    {"key": "goals", "icon": "🎯", "name": "Goals", "path": "/goals",
     "description": "Goal tracking with natural-language updates.",
     "version": "1.0", "released": "2026-06-16", "requires": ["anthropic"]},
    {"key": "wins", "icon": "🌟", "name": "Wins", "path": "/wins",
     "description": "Daily wins with AI recognition.",
     "version": "1.0", "released": "2026-06-16", "requires": ["anthropic"]},
    {"key": "nominal", "icon": "💰", "name": "Nominal", "path": "/nominal",
     "description": "Budget by Fixed / Loose / Float / Savings, with audience masking.",
     "version": "1.0", "released": "2026-06-17", "requires": []},
    {"key": "body", "icon": "🫀", "name": "Body", "path": "/body",
     "description": "Meds, weight journey, and habits — private by default.",
     "version": "1.0", "released": "2026-06-17", "requires": []},
    {"key": "wealth", "icon": "📊", "name": "Wealth", "path": "/wealth",
     "description": "Investments + retirement projections, with audience masking.",
     "version": "1.0", "released": "2026-06-17", "requires": []},
    {"key": "trips", "icon": "✈️", "name": "Trips", "path": "/trips",
     "description": "Travel planner with per-audience notes and to-dos.",
     "version": "1.0", "released": "2026-06-17", "requires": []},
    {"key": "wellness", "icon": "🌸", "name": "Wellness", "path": "/wellness",
     "description": "Daily non-negotiables, routine, and life rules.",
     "version": "1.0", "released": "2026-06-17", "requires": []},
    {"key": "career", "icon": "💼", "name": "Career", "path": "/career",
     "description": "Job search: applications, prep notes, and a to-do checklist.",
     "version": "1.0", "released": "2026-06-18", "requires": []},
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
