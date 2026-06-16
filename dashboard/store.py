"""Tiny JSON file store for dashboard module data.

There's no database yet, so module state (About text + photo, and later
Stocks/Goals/Wins) lives in JSON files under dashboard/data/.

NOTE / open decision: on Render the filesystem is **ephemeral** — these files
reset on every redeploy or restart. Real persistence (a database, or a Render
persistent disk + object storage for images) is an open decision that affects
every editable module. Until then, edits survive a running session but not a
redeploy. See each module's TODO.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"


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
