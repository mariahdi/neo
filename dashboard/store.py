"""Tiny JSON file store for dashboard module data.

There's no database yet, so module state (About text + photo, and later
Stocks/Goals/Wins) lives in JSON files under dashboard/data/.

By default these files live next to the code (dashboard/data/), which on
Render is **ephemeral** — they reset on every redeploy or restart. To make
them durable, set **NEO_DATA_DIR** to a path on a mounted persistent disk
(e.g. /var/data); the store writes there instead. See docs/DEPLOY.md for the
one-time disk setup. Nothing else changes — same JSON files, durable location.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Durable when NEO_DATA_DIR points at a mounted disk; ephemeral otherwise.
_DATA_DIR = Path(os.environ.get("NEO_DATA_DIR") or (Path(__file__).resolve().parent / "data"))


def _path(name: str) -> Path:
    return _DATA_DIR / f"{name}.json"


def load(name: str, default: Any) -> Any:
    """Return the stored value for `name`, or `default` if absent/unreadable."""
    try:
        return json.loads(_path(name).read_text())
    except (FileNotFoundError, ValueError):
        return default


def save(name: str, data: Any) -> None:
    """Persist `data` for `name` as pretty JSON (creates the data dir)."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _path(name).write_text(json.dumps(data, indent=2))
