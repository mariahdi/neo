#!/usr/bin/env bash
# Validate the NEO_* credentials before a live run (python -m neo --live).
#
# Checks all four secrets against their real APIs so you catch a bad or
# placeholder key here instead of mid-run:
#   - Jira      (NEO_JIRA_EMAIL + NEO_JIRA_API_TOKEN)  -> /rest/api/3/myself
#   - Anthropic (NEO_ANTHROPIC_API_KEY)                -> /v1/models
#   - GitHub    (NEO_GITHUB_TOKEN)                     -> /user + repo push perm
#
# Base URL and repo default to this project's config if unset. The GitHub
# check makes ONE reversible write (creates a temp branch off the default
# branch, then deletes it) to truly verify push access — a read of
# permissions.push can't see a fine-grained token's missing Contents:write.
# Everything else is read-only. Exit code is 0 only if every check passes.

set -uo pipefail

BASE="${NEO_JIRA_BASE_URL:-https://mariahdiharris.atlassian.net}"
REPO="${NEO_GITHUB_REPO:-mariahdi/neo}"

pass=0
fail=0
ok()   { printf "  [ OK ] %s\n" "$1"; pass=$((pass+1)); }
bad()  { printf "  [FAIL] %s\n" "$1"; fail=$((fail+1)); }

# Empty, or still the literal "<placeholder>" from the README example.
is_placeholder() {
  local v="${1:-}"
  [ -z "$v" ] || [[ "$v" == *"<"*">"* ]]
}

echo "Checking NEO_* credentials..."
echo

# ── Jira ──────────────────────────────────────────────────────────────────────
echo "Jira ($BASE)"
if is_placeholder "${NEO_JIRA_EMAIL:-}" || is_placeholder "${NEO_JIRA_API_TOKEN:-}"; then
  bad "NEO_JIRA_EMAIL / NEO_JIRA_API_TOKEN not set (or still a placeholder)"
else
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 15 \
    -u "$NEO_JIRA_EMAIL:$NEO_JIRA_API_TOKEN" "$BASE/rest/api/3/myself")
  case "$code" in
    200) ok  "authenticated as $NEO_JIRA_EMAIL" ;;
    401|403) bad "auth rejected (HTTP $code) — wrong email or token" ;;
    404) bad "HTTP 404 — token not authenticating (Jira hides issues from anonymous calls)" ;;
    *)   bad "unexpected HTTP $code from /myself" ;;
  esac
fi
echo

# ── Anthropic ─────────────────────────────────────────────────────────────────
echo "Anthropic"
if is_placeholder "${NEO_ANTHROPIC_API_KEY:-}"; then
  bad "NEO_ANTHROPIC_API_KEY not set (or still a placeholder)"
else
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 15 \
    -H "x-api-key: $NEO_ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" \
    https://api.anthropic.com/v1/models)
  case "$code" in
    200) ok  "key valid" ;;
    401) bad "auth rejected (HTTP 401) — invalid API key" ;;
    *)   bad "unexpected HTTP $code from /v1/models" ;;
  esac
fi
echo

# ── GitHub ────────────────────────────────────────────────────────────────────
echo "GitHub ($REPO)"
if is_placeholder "${NEO_GITHUB_TOKEN:-}"; then
  bad "NEO_GITHUB_TOKEN not set (or still a placeholder)"
else
  gh_h=(-H "Authorization: Bearer $NEO_GITHUB_TOKEN"
        -H "Accept: application/vnd.github+json"
        -H "X-GitHub-Api-Version: 2022-11-28")
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 15 "${gh_h[@]}" https://api.github.com/user)
  if [ "$code" != "200" ]; then
    bad "auth rejected (HTTP $code) — invalid token"
  else
    ok "token valid"
    repo_json=$(curl -s -m 15 "${gh_h[@]}" "https://api.github.com/repos/$REPO")
    if ! echo "$repo_json" | grep -q '"id"'; then
      bad "cannot access $REPO — the token's Repository access doesn't include it"
    else
      ok "can see $REPO"
      # Real write probe: create a throwaway ref off the default branch (the
      # exact op the live run does via POST /git/refs), then delete it.
      default_branch=$(printf '%s' "$repo_json" | sed -n 's/.*"default_branch":[[:space:]]*"\([^"]*\)".*/\1/p')
      default_branch="${default_branch:-main}"
      base_sha=$(curl -s -m 15 "${gh_h[@]}" \
        "https://api.github.com/repos/$REPO/git/ref/heads/$default_branch" \
        | sed -n 's/.*"sha":[[:space:]]*"\([0-9a-f]\{40\}\)".*/\1/p' | head -1)
      if [ -z "$base_sha" ]; then
        bad "couldn't read '$default_branch' to test write access"
      else
        tmp_ref="neo-credcheck-$$"
        create_code=$(curl -s -o /dev/null -w "%{http_code}" -m 15 "${gh_h[@]}" \
          -X POST "https://api.github.com/repos/$REPO/git/refs" \
          -d "{\"ref\":\"refs/heads/$tmp_ref\",\"sha\":\"$base_sha\"}")
        case "$create_code" in
          201)
            ok "write access confirmed (Contents: write)"
            del_code=$(curl -s -o /dev/null -w "%{http_code}" -m 15 "${gh_h[@]}" \
              -X DELETE "https://api.github.com/repos/$REPO/git/refs/heads/$tmp_ref")
            [ "$del_code" = "204" ] || printf "         note: couldn't auto-delete temp branch '%s' (HTTP %s) — remove it on GitHub\n" "$tmp_ref" "$del_code"
            ;;
          403) bad "token can READ $REPO but not WRITE — grant Contents: Read and write (+ Pull requests: Read and write)" ;;
          422) bad "write test inconclusive (HTTP 422) — base ref/sha problem" ;;
          *)   bad "write test failed (HTTP $create_code)" ;;
        esac
      fi
    fi
  fi
fi
echo

# ── Summary ───────────────────────────────────────────────────────────────────
echo "── $pass passed, $fail failed ──"
if [ "$fail" -eq 0 ]; then
  echo "All set. You're clear to run: python -m neo --live"
  exit 0
else
  echo "Fix the failures above, then re-run ./check-creds.sh"
  exit 1
fi
