# Integrations

Neo holds no secrets. Live integrations read credentials from the
environment. Right now **Jira is live**; GitHub and Claude are still dry
stubs (next to wire).

## Jira (live)

### 1. Create an API token
Go to https://id.atlassian.com/manage-profile/security/api-tokens →
**Create API token**. Copy it somewhere safe.

### 2. Set the environment variables
```bash
export NEO_JIRA_BASE_URL="https://mariahdiharris.atlassian.net"
export NEO_JIRA_EMAIL="you@example.com"
export NEO_JIRA_API_TOKEN="paste-the-token"
```
(Put these in your shell profile, or a local `.env` you don't commit.)

### 3. Add the "In Review" column to the board
The default board is To Do → In Progress → Done. Neo's workflow needs a
fourth stage. In Jira: **Project settings → Board → Columns →** add a
column named **In Review** between In Progress and Done. Until you do, Neo
will skip that transition and say so rather than failing.

### 4. Run it live
```bash
python -m neo --live
```
By default this only acts on the hot item (NEO-2, which exists on the
board): it moves NEO-2 to In Progress, then In Review. The queued item
(NEO-3) is just a sample and isn't on the board — don't `--force-start`
live until you've created it.

If anything is misconfigured, Neo prints the Jira error (status + message)
instead of crashing.

## GitHub (live)

### 1. Create a token
GitHub → Settings → Developer settings → **Fine-grained personal access
tokens** → scope it to the `neo` repo with **Contents** and **Pull
requests** set to read/write.

### 2. Set the environment variables
```bash
export NEO_GITHUB_REPO="mariahdi/neo"
export NEO_GITHUB_TOKEN="github_pat_..."
```

### What `--live` now does for a hot item
1. Jira: NEO-2 → In Progress
2. GitHub: create `feature/NEO-2` (reuses it if it already exists)
3. GitHub: commit the draft to `proposals/NEO-2.md` on that branch
4. GitHub: open a pull request (reuses the open PR if one exists)
5. Jira: NEO-2 → In Review

Branch and PR creation are idempotent — re-running won't error if they
already exist.

> **Two things to know before running live:**
> - **Claude isn't wired yet**, so the committed draft is still placeholder
>   text. A live run right now opens a real PR containing that placeholder.
>   If you'd rather the first real PR have a real draft, wire Claude first.
> - **The repo is public.** Anything Neo commits (the proposal drafts) is
>   public too. For real client proposals, make the repo private or point
>   proposal content at a separate private repo.

## What each client does

| Client      | Status    | Backed by                               |
|-------------|-----------|-----------------------------------------|
| Jira        | **live**  | Atlassian REST API v3 (stdlib urllib)   |
| GitHub      | **live**  | GitHub REST API (stdlib urllib)         |
| Claude      | dry stub  | next: Anthropic Messages API            |

Swapping a stub for a live client is local to `neo/integrations.py` — the
loop doesn't change.


