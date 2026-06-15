"""Configuration for Neo.

Neo itself holds no personal data. It only holds *paths* to where the
private data layer lives, plus integration settings. Real secrets are
read from the environment, never committed.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "config" / "neo.config.json"
EXAMPLE_CONFIG = REPO_ROOT / "config" / "neo.config.example.json"


@dataclass
class Config:
    personal_data_dir: Path
    enabled_modules: list[str]
    # Integration credentials come from the environment, not the file.
    jira_base_url: str = ""
    github_repo: str = ""

    @property
    def skills_dir(self) -> Path:
        return self.personal_data_dir / "skills"

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or (DEFAULT_CONFIG if DEFAULT_CONFIG.exists() else EXAMPLE_CONFIG)
        raw = json.loads(Path(path).read_text())
        pd = Path(raw["personal_data_dir"])
        if not pd.is_absolute():
            pd = (REPO_ROOT / pd).resolve()
        return cls(
            personal_data_dir=pd,
            enabled_modules=raw.get("enabled_modules", []),
            jira_base_url=os.environ.get("NEO_JIRA_BASE_URL", raw.get("jira_base_url", "")),
            github_repo=os.environ.get("NEO_GITHUB_REPO", raw.get("github_repo", "")),
        )
