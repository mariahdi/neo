"""Active instance profile — the personalization layer (NEO-36).

One codebase, many instances. A profile is pure config (JSON in profiles/):
name + wordmark, theme tokens (colors + fonts), and a role. The running
instance is chosen by the NEO_PROFILE env var (default "neo"); set
NEO_PROFILE=aria on Aria's deploy. Engine code stays generic — only the
profile differs, so dev benefits every instance and there's no fork.

Add a new instance = drop a profiles/<name>.json and set NEO_PROFILE.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_DIR = Path(__file__).resolve().parent / "profiles"
_DEFAULT = "neo"


def _load() -> dict:
    name = os.environ.get("NEO_PROFILE", _DEFAULT).strip() or _DEFAULT
    path = _DIR / f"{name}.json"
    if not path.exists():
        path = _DIR / f"{_DEFAULT}.json"
    return json.loads(path.read_text(encoding="utf-8"))


# Resolved once at import — the profile doesn't change within a running process.
ACTIVE = _load()


def root_css() -> str:
    """The :root CSS variable block for the active profile's theme tokens."""
    tokens = ACTIVE.get("tokens", {})
    body = "".join(f"    --{k}: {v};\n" for k, v in tokens.items())
    return ":root {\n" + body + "  }"


def who() -> str:
    """Effective display name — a runtime override (set on /me) or the profile default."""
    from . import store  # local import to avoid any import-order surprises
    return (store.load("me", {}) or {}).get("name") or ACTIVE.get("who", "")


def pronouns() -> str:
    from . import store
    return (store.load("me", {}) or {}).get("pronouns") or ACTIVE.get("pronouns", "")
