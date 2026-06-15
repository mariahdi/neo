"""The skill loader.

Skills (e.g. "nonprofit-proposal", "government-contract") live in the
PRIVATE personal-data layer and are never committed publicly. Neo knows
how to fetch and apply them, but the substance stays in your data layer.

Inference is deliberately dumb-but-overridable: a keyword map picks a
default skill, and an explicit skill on the work item always wins.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

# Default skill inference. Explicit WorkItem.skill overrides all of this.
_KEYWORD_MAP: dict[str, str] = {
    "red cross": "nonprofit-proposal",
    "nonprofit": "nonprofit-proposal",
    "non-profit": "nonprofit-proposal",
    "charity": "nonprofit-proposal",
    "government": "government-contract",
    "federal": "government-contract",
    "air force": "government-contract",
    "rfp": "government-contract",
}


def infer_skill(request: str) -> Optional[str]:
    text = request.lower()
    for kw, skill in _KEYWORD_MAP.items():
        if kw in text:
            return skill
    return None


class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir

    def load(self, skill: str) -> str:
        """Return the skill's instructions. Looks for a real skill first,
        then an .example stub, so the scaffold runs before you've added
        your private skills."""
        real = self.skills_dir / f"{skill}.md"
        example = self.skills_dir / f"{skill}.example.md"
        if real.exists():
            return real.read_text()
        if example.exists():
            return example.read_text()
        raise FileNotFoundError(
            f"No skill '{skill}' in {self.skills_dir}. "
            f"Add {skill}.md to your private data layer."
        )
