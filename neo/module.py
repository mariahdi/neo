"""Module contract.

Every module (proposals, landlord, ...) is a self-contained piece that
the loop executes only when enabled. A module takes a WorkItem plus a
context of shared clients, does its work, and advances the item's state.

Sensitive modules can keep their own data sealed off and report back only
status — they never have to hand details to the central loop.
"""
from __future__ import annotations

from dataclasses import dataclass

from .integrations import (ClaudeClient, DryGitHubClient, DryJiraClient,
                           LiveGitHubClient, LiveJiraClient)
from .skill_loader import SkillLoader
from .types import WorkItem


@dataclass
class Context:
    jira: DryJiraClient | LiveJiraClient
    github: DryGitHubClient | LiveGitHubClient
    claude: ClaudeClient
    skills: SkillLoader


class Module:
    name: str = "base"

    def handle(self, item: WorkItem, ctx: Context) -> WorkItem:  # pragma: no cover
        raise NotImplementedError
