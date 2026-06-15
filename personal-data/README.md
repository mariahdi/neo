# Private data layer

**Nothing real in here gets committed.** This is the substance: templates,
past proposals, pricing, client details, and skills. The Neo loop reads
from this folder but never exposes it.

`.gitignore` keeps `data.json` and real `skills/*.md` out of version
control. The `*.example.*` files are safe, content-free stubs that let the
scaffold run before you've added anything private.

To go live:
1. Copy `data.example.json` -> `data.json` and fill it in.
2. Copy a skill stub, e.g. `skills/nonprofit-proposal.example.md`
   -> `skills/nonprofit-proposal.md`, and write your real approach.
