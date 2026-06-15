"""The router.

Part of the Neo loop's job: decide which module a request belongs to,
and infer a default skill. The router holds no data — it just maps
requests onto enabled modules.
"""
from __future__ import annotations

from .skill_loader import infer_skill
from .neo_types import WorkItem

# Keyword -> module. First match wins. Extend as modules come online.
_MODULE_MAP: list[tuple[tuple[str, ...], str]] = [
    (("proposal", "rfp", "red cross", "bid"), "proposals"),
    (("tenant", "landlord", "lease", "maintenance"), "landlord"),
    (("website", "web dev", "deploy", "air force site"), "airforce_web"),
]


def route(item: WorkItem, enabled_modules: list[str]) -> WorkItem:
    """Fill in item.module and item.skill if not already set."""
    if not item.module:
        text = f"{item.title} {item.request}".lower()
        for keywords, module in _MODULE_MAP:
            if any(k in text for k in keywords):
                item.module = module
                break
    if item.module and item.module not in enabled_modules:
        item.log(f"module '{item.module}' is not enabled — queued, not started")
    if item.skill is None:
        item.skill = infer_skill(item.request)
    return item
