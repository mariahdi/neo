"""USAFA module — Air Force Academy website / web-dev tasks.

Same shape as the proposals module, but for website work. Given a routed
work item, it:
  1. loads the right web skill from the private data layer,
  2. asks Claude to produce the website change (markup/code + a clear,
     reviewable description),
  3. checks out feature/<KEY>, commits the change into the repo so reviewers
     can see it inline, and opens a pull request.

The loop then moves the ticket to In Review for human sign-off before it ships.
"""
from __future__ import annotations

from neo.module import Context, Module
from neo.neo_types import WorkItem


class UsafaModule(Module):
    name = "usafa"

    def handle(self, item: WorkItem, ctx: Context) -> WorkItem:
        skill_name = item.skill or "usafa-web"
        try:
            skill_text = ctx.skills.load(skill_name)
        except FileNotFoundError as e:
            item.log(str(e))
            skill_text = "(no skill found — drafting from the request alone)"

        change = ctx.claude.draft(item.request, skill_text)

        ctx.github.checkout_branch(item.branch)
        ctx.github.commit_file(item.branch, f"usafa-site/{item.key}.md", change)
        pr_url = ctx.github.open_pull_request(item.branch, item.title)

        item.log(f"used skill '{skill_name}'")
        item.log(f"opened PR {pr_url}")
        return item


MODULE = UsafaModule()
