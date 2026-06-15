"""Core types for Neo: the work item and its lifecycle states.

The state model mirrors the plan:

    BRAIN -> TODO -> IN_PROGRESS -> IN_REVIEW -> DONE
                         ^                          |
                         +------ (owner rejects) ---+
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class State(str, Enum):
    BRAIN = "brain"            # spoken, not yet captured
    TODO = "to_do"            # captured as a ticket, queued
    IN_PROGRESS = "in_progress"  # Claude / a person is working it
    IN_REVIEW = "in_review"   # draft open, awaiting human sign-off
    DONE = "done"             # owner approved


class Category(str, Enum):
    HOT = "hot"        # auto-starts immediately
    STANDARD = "standard"  # queues until the owner says go
    LOW = "low"


@dataclass
class WorkItem:
    """One unit of work. Becomes a Jira ticket (e.g. NEO-2) and a
    branch (feature/NEO-2)."""
    key: str                       # e.g. "NEO-2"
    title: str                     # e.g. "Proposal — American Red Cross"
    request: str                   # the owner's spoken request, verbatim
    module: str                    # which module owns it, e.g. "proposals"
    category: Category = Category.STANDARD
    skill: Optional[str] = None    # inferred or explicit, e.g. "nonprofit-proposal"
    est_minutes: Optional[int] = None
    state: State = State.TODO
    branch: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    @property
    def should_auto_start(self) -> bool:
        """Hot items start themselves; everything else waits for a go."""
        return self.category is Category.HOT

    def log(self, msg: str) -> None:
        self.notes.append(msg)
