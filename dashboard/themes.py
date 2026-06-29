"""Per-user theme picker (NEO) — switch the whole look on screen, saved per user.

Each theme is a full color-token set. The chosen one is injected as a :root
override *after* the base stylesheet, so it wins without touching the profile
defaults. No choice = the instance's own profile theme. Fonts inherit from the
profile; only colors switch.

Stored per-user under "theme" (so each person picks their own, thanks to the
per-user store scoping).
"""
from __future__ import annotations

from . import store

# Display order matters. Cornflower is the light, gentle default; the rest are
# the deeper, cooler blues.
PRESETS: dict[str, dict] = {
    "cornflower": {
        "label": "Cornflower",
        "tokens": {
            "bg": "#e3ebf8", "bg-2": "#d9e3f4", "bg-glow": "#eaf0fe",
            "panel": "#f4f2fa", "panel-2": "#ece9f5", "line": "#cdd8ec",
            "line-soft": "#dde5f3", "text": "#36405a", "muted": "#7882a0",
            "gold": "#4f8fe6", "gold-soft": "rgba(79,143,230,0.15)",
            "gold-line": "rgba(79,143,230,0.42)", "hot": "#f0a07a",
            "gold-hover": "#6aa3ef", "on-gold": "#ffffff",
            "field": "#f6f6fb", "btn-bg": "#ece9f5",
        },
    },
    "mocha": {
        "label": "Mocha",
        "tokens": {
            "bg": "#0e0a07", "bg-2": "#1a120c", "bg-glow": "#2a1c10",
            "panel": "#1c1410", "panel-2": "#241a12", "line": "#3a2d20",
            "line-soft": "#2a2016", "text": "#f5ede0", "muted": "#a08060",
            "gold": "#e8a87c", "gold-soft": "rgba(232,168,124,0.14)",
            "gold-line": "rgba(232,168,124,0.42)", "hot": "#f0a07a",
            "gold-hover": "#f0bc92", "on-gold": "#1a1305",
            "field": "#1a1410", "btn-bg": "#241a12",
        },
    },
    "midnight": {
        "label": "Midnight",
        "tokens": {
            "bg": "#0e1626", "bg-2": "#131e33", "bg-glow": "#18243f",
            "panel": "#16213a", "panel-2": "#1c2a47", "line": "#2b3d61",
            "line-soft": "#21304e", "text": "#e6edf8", "muted": "#93a6c6",
            "gold": "#5b9cf0", "gold-soft": "rgba(91,156,240,0.16)",
            "gold-line": "rgba(91,156,240,0.45)", "hot": "#6fb4e8",
            "gold-hover": "#79b0f5", "on-gold": "#0b1220",
            "field": "#16213a", "btn-bg": "#1c2a47",
        },
    },
    "ocean": {
        "label": "Deep Ocean",
        "tokens": {
            "bg": "#08191f", "bg-2": "#0d242c", "bg-glow": "#103038",
            "panel": "#0f2a31", "panel-2": "#143a43", "line": "#205662",
            "line-soft": "#1a414b", "text": "#e1f0f2", "muted": "#84b2b8",
            "gold": "#34b6c2", "gold-soft": "rgba(52,182,194,0.16)",
            "gold-line": "rgba(52,182,194,0.45)", "hot": "#5fcad6",
            "gold-hover": "#50c4d0", "on-gold": "#06161b",
            "field": "#0f2a31", "btn-bg": "#143a43",
        },
    },
    "slate": {
        "label": "Slate",
        "tokens": {
            "bg": "#0f141b", "bg-2": "#161d27", "bg-glow": "#1b2533",
            "panel": "#19212c", "panel-2": "#212c3a", "line": "#314256",
            "line-soft": "#25313f", "text": "#e7ecf3", "muted": "#94a3b8",
            "gold": "#7aa7d6", "gold-soft": "rgba(122,167,214,0.16)",
            "gold-line": "rgba(122,167,214,0.45)", "hot": "#93b4d6",
            "gold-hover": "#8db6e0", "on-gold": "#0c1118",
            "field": "#19212c", "btn-bg": "#212c3a",
        },
    },
    "indigo": {
        "label": "Indigo",
        "tokens": {
            "bg": "#100e20", "bg-2": "#19162f", "bg-glow": "#221c40",
            "panel": "#1c1839", "panel-2": "#261f49", "line": "#38305f",
            "line-soft": "#29214a", "text": "#ece9f8", "muted": "#9d93c6",
            "gold": "#8b7cf0", "gold-soft": "rgba(139,124,240,0.16)",
            "gold-line": "rgba(139,124,240,0.45)", "hot": "#a594f5",
            "gold-hover": "#9b8cf5", "on-gold": "#0c0a18",
            "field": "#1c1839", "btn-bg": "#261f49",
        },
    },
    "rose": {
        "label": "Rose",
        "tokens": {
            "bg": "#160f12", "bg-2": "#1f161a", "bg-glow": "#2a1c22",
            "panel": "#201619", "panel-2": "#2a1e23", "line": "#3e2c33",
            "line-soft": "#2d2025", "text": "#f3e7ea", "muted": "#b08f99",
            "gold": "#e08aa0", "gold-soft": "rgba(224,138,160,0.15)",
            "gold-line": "rgba(224,138,160,0.42)", "hot": "#f0a0b0",
            "gold-hover": "#ec9cb0", "on-gold": "#1a0f12",
            "field": "#201619", "btn-bg": "#2a1e23",
        },
    },
    "forest": {
        "label": "Forest",
        "tokens": {
            "bg": "#0c130e", "bg-2": "#121d15", "bg-glow": "#16271b",
            "panel": "#14201a", "panel-2": "#1a2c22", "line": "#274536",
            "line-soft": "#1e3328", "text": "#e6f0e8", "muted": "#8fb29c",
            "gold": "#7fb98a", "gold-soft": "rgba(127,185,138,0.15)",
            "gold-line": "rgba(127,185,138,0.42)", "hot": "#9fd0a8",
            "gold-hover": "#93c79e", "on-gold": "#0a140d",
            "field": "#14201a", "btn-bg": "#1a2c22",
        },
    },
}


def current() -> str:
    """The current user's chosen theme key, or "" for the profile default."""
    name = store.load("theme", "") or ""
    return name if name in PRESETS else ""


def set_theme(name: str) -> bool:
    """Save the chosen theme. "" / "default" clears back to the profile theme."""
    if name in PRESETS:
        store.save("theme", name)
        return True
    if name in ("", "default"):
        store.save("theme", "")
        return True
    return False


def override_css() -> str:
    """A :root{} block for the chosen theme, or "" when on the profile default."""
    name = current()
    if not name:
        return ""
    tokens = PRESETS[name]["tokens"]
    return ":root{" + "".join(f"--{k}:{v};" for k, v in tokens.items()) + "}"


def options() -> list[dict]:
    """Picker data: key, label, and two preview colors (bg + accent)."""
    return [
        {"key": k, "label": v["label"],
         "bg": v["tokens"]["bg"], "accent": v["tokens"]["gold"]}
        for k, v in PRESETS.items()
    ]
