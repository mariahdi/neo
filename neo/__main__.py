"""Neo CLI.

    python -m neo --dry-run     narrate the proposals loop on a sample item
    python -m neo --help        options

The dry run uses the same NEO-2 example that's in the Jira board, so you
can show the flow end to end without touching any live integration.
"""
from __future__ import annotations

import argparse

from .config import Config
from .loop import NeoLoop
from .types import Category, WorkItem


def _sample_items() -> list[WorkItem]:
    return [
        WorkItem(
            key="NEO-2",
            title="Proposal — American Red Cross",
            request="Write a proposal for the American Red Cross. Send it to my proposals group.",
            module="",                 # let the router decide
            category=Category.HOT,     # hot -> auto-starts
            est_minutes=5,
        ),
        WorkItem(
            key="NEO-3",
            title="Proposal — County library RFP",
            request="Draft a bid for the county library RFP.",
            module="",
            category=Category.STANDARD,  # queues until the owner says go
            est_minutes=20,
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(prog="neo", description="Neo orchestration loop")
    parser.add_argument("--dry-run", action="store_true",
                        help="narrate the loop without calling live integrations")
    parser.add_argument("--force-start", action="store_true",
                        help="start queued (non-hot) items too")
    args = parser.parse_args()

    config = Config.load()
    loop = NeoLoop(config)

    print("Neo — dry run\n" if args.dry_run else "Neo\n")
    print(f"enabled modules: {', '.join(config.enabled_modules) or '(none)'}")
    print(f"private data: {config.personal_data_dir}\n")

    items = loop.tick(_sample_items(), force_start=args.force_start)

    print("\nresult:")
    for it in items:
        print(f"  {it.key:7} {it.state.value:12} skill={it.skill or '-'} branch={it.branch or '-'}")


if __name__ == "__main__":
    main()
