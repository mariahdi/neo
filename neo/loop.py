"""The Neo main loop.

Modeled on a flight-software control loop: a single main loop with a
sequencer that, each tick, runs the same ordered steps over the current
work. Clean, predictable, and easy to reason about.

Per tick, for each work item that is ready:
    1. route   — decide module + skill
    2. gate    — hot auto-starts; standard/low wait for a go
    3. execute — hand to the module (which drafts + opens review)
    4. report  — advance Jira state

This file deliberately does no I/O of its own beyond the injected clients,
so it can run as a dry narration or against real integrations unchanged.
"""
from __future__ import annotations

import importlib
from typing import Iterable

from .config import Config
from .integrations import (ClaudeClient, ConsoleReporter, GitHubClient,
                           JiraClient, Reporter)
from .module import Context, Module
from .router import route
from .skill_loader import SkillLoader
from .types import State, WorkItem


def _load_module(name: str) -> Module:
    """Modules live under modules/<name>/module.py and expose `MODULE`."""
    mod = importlib.import_module(f"modules.{name}.module")
    return getattr(mod, "MODULE")


class NeoLoop:
    def __init__(self, config: Config, reporter: Reporter | None = None):
        self.config = config
        self.reporter = reporter or ConsoleReporter()
        self.ctx = Context(
            jira=JiraClient(config.jira_base_url, self.reporter),
            github=GitHubClient(config.github_repo, self.reporter),
            claude=ClaudeClient(self.reporter),
            skills=SkillLoader(config.skills_dir),
        )
        self._modules: dict[str, Module] = {}

    def _module(self, name: str) -> Module:
        if name not in self._modules:
            self._modules[name] = _load_module(name)
        return self._modules[name]

    def tick(self, items: Iterable[WorkItem], force_start: bool = False) -> list[WorkItem]:
        """Run one pass of the sequencer over the given work items."""
        out: list[WorkItem] = []
        for item in items:
            self.reporter.say(f"── {item.key}: {item.title}")
            route(item, self.config.enabled_modules)

            if not (item.should_auto_start or force_start):
                item.log("queued — waiting for the owner to say go")
                self.reporter.say("queued (not hot) — skipping this tick")
                out.append(item)
                continue

            if item.module not in self.config.enabled_modules:
                item.log("module not enabled — cannot start yet")
                self.reporter.say(f"module '{item.module}' not enabled — skipping")
                out.append(item)
                continue

            item.branch = f"feature/{item.key}"
            item.state = State.IN_PROGRESS
            self.ctx.jira.transition(item.key, State.IN_PROGRESS.value)

            self._module(item.module).handle(item, self.ctx)

            item.state = State.IN_REVIEW
            self.ctx.jira.transition(item.key, State.IN_REVIEW.value)
            self.reporter.say("awaiting human sign-off, then owner approval")
            out.append(item)
        return out
