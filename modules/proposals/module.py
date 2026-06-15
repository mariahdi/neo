"""Proposals module — the proof of concept.

Given a routed work item, it:
  1. loads the right proposal skill from the private data layer,
  2. asks Claude to draft the proposal,
  3. checks out feature/<KEY>, commits the draft into the repo so reviewers
     can comment inline, and opens a pull request.

The loop then moves the ticket to In Review for human sign-off.
"""
from __future__ import annotations

from neo.module import Context, Module
from neo.types import WorkItem


class ProposalsModule(Module):
    name = "proposals"

    def handle(self, item: WorkItem, ctx: Context) -> WorkItem:
        skill_name = item.skill or "general-proposal"
        try:
            skill_text = ctx.skills.load(skill_name)
        except FileNotFoundError as e:
            item.log(str(e))
            skill_text = "(no skill found — drafting from the request alone)"

        draft = ctx.claude.draft(item.request, skill_text)

        ctx.github.checkout_branch(item.branch)
        ctx.github.commit_file(item.branch, f"proposals/{item.key}.md", draft)
        pr_url = ctx.github.open_pull_request(item.branch, item.title)

        item.log(f"used skill '{skill_name}'")
        item.log(f"opened PR {pr_url}")
        return item


MODULE = ProposalsModule()
