---
name: one-shot-this
description: |
  Explicit skill. Given a Jira issue key, fetch the approved contract through the configured Jira CLI or connector, identify impacted
  repositories through the service catalog, and preserve Jira requirements through code, GitHub, and CI handoffs. Implement a
  single-repository change in the current Codex session; only use tmux workers and git worktrees for multiple repositories.
---

# Workflow (must follow exactly)

## Inputs
- Jira story key (e.g., DEMO-123)
- Environment variables (if set):
  - WORKSPACE_ROOT: folder that contains local clones of repos (default: current directory)
  - BASE_BRANCH: default base branch for worktrees (default: main)

## Step 1 — Requirements intake (read-only)
1) Prefer the configured Jira CLI for an exact issue read; use an available Jira connector for broad discovery or when the CLI cannot perform the read.
2) Fetch and retain:
   - key and full Jira URL
   - issue type, title, description, acceptance criteria, status, and ownership boundary
   - validation, E2E, observability, rollout, links, and attachments
3) Read linked blockers or dependencies that can change implementation order.
4) Summarize requirements and list assumptions/questions. Do not silently replace Jira scope with an implementation guess.

## Step 2 — Repo selection using service catalog (read-only)
1) Use service-catalog MCP to find impacted repos/services.
2) Read each selected service through `get_service`, including its `last_verified` value.
3) If `last_verified` is missing or too old for the decision, confirm important routing claims against the current repository. When the catalog is missing a repository, use `generate-service-description` to propose or create the missing index only when the user has authorized repository changes.
4) Produce a list of repos with:
   - why impacted
   - key modules/files likely touched
   - integration/dependency notes

## Step 3 — Plan
Output a structured plan with:
- `jira_key`, `jira_url`, `issue_type`, `summary`, `description`, and `acceptance_criteria[]`
- `repos`: list of `{ name, local_path (if known), branch_suffix, branch_type (optional), why_impacted, acceptance_criteria[] (optional repo subset), steps[], tests[], observability[], rollout_notes[] }`
- `cross_repo_steps[]` and `dependency_links[]` when applicable

The full Jira URL, description, and acceptance criteria are required handoff fields. Map a criterion to specific repositories when ownership is narrower than the whole change. Do not generate work packets until the contract fields are present.
Then ask for approval:
- For exactly one repo: "Approve implementation in <repo> in this session?"
- For two or more repos: "Approve to generate work packets + spawn tmux workers?"

STOP if not approved.

## Step 4A — Single repo: implement in the current session
When the approved plan contains exactly one repo:
1) Do not run `scripts/write_work_packets.py` or `scripts/spawn_tmux_worktrees.sh`.
2) Do not create a tmux worker or a git worktree. Continue in the current Codex session and work directly in the selected repo.
3) Implement the approved repo plan, run its listed tests, and follow the implementation rules below.
4) Preserve the Jira URL and acceptance-criteria mapping in the eventual pull request and CI handoff.
5) Report the normal implementation outcome directly; do not return a `tmux attach` instruction.

## Step 4B — Multiple repos: generate work packets + spawn tmux workers
Only when the approved plan contains two or more repos:
1) Run scripts/write_work_packets.py to write one markdown packet per repo into ./run/packets/
2) Run scripts/spawn_tmux_worktrees.sh to:
   - create a worktree per repo
   - open a tmux session with one pane per repo
   - start a Codex session in each pane, feeding it the repo’s packet
   - note: the launcher canonicalizes `<plan.json>` and `<packets_dir>` to absolute paths, so callers can pass relative paths safely
3) After spawn succeeds, do not run extra tmux verification commands.
4) Final response for this step must be a single instruction line:
   - `tmux attach -t codex-<JIRA_KEY>`

## Implementation rules (current session or spawned workers)
- Operate only within the selected repo or assigned worktree.
- Implement the approved plan, using the generated packet when running as a spawned worker.
- Run the tests listed in the approved plan or generated packet.
- Branch naming defaults to `feature/<branch_suffix>`. Use `bugfix/<branch_suffix>` only when the story explicitly indicates a bug fix or the plan sets `branch_type: bugfix`.
- Before any push or PR, explicitly ask:
  "Approve push + draft PR + Jira link for <repo>?"
- If approved:
  - ensure the current local branch tracks `origin/<current-branch>` (do not only check that some upstream exists)
  - if tracking is missing or points elsewhere (for example `origin/main`), set/fix it by pushing with upstream tracking (for example `git push -u origin <branch>`)
  - create a draft PR whose description includes the full Jira URL, acceptance-criteria mapping, tests, observability, and rollout notes
  - link the PR URL back to Jira through the configured CLI or connector, then read the saved Jira link/comment back
  - inspect GitHub checks; when a check points to Jenkins, use `jenkins-pipeline-checker` rather than guessing from incomplete GitHub output
- Report back with:
  - branch name
  - PR link
  - Jira link-back result
  - tests run + results
  - GitHub/Jenkins check status and source URLs when available
  - any follow-ups/risks

## Gradle worktree reliability (Nebula/Grgit)
- Only for repos that use Gradle, run Gradle tests in spawned worktrees via `./.codex-gradle-test.sh`.
- The launcher only copies this wrapper when the worktree contains `./gradlew`.
- The launcher uses `${SHELL}` when present instead of assuming Bash.
- Gradle worktrees should use the user's normal Gradle configuration from `~/.gradle` by default.
- A workspace-local Gradle configuration may override the default when the launched workspace intentionally provides one.
- This wrapper exists to make Gradle run safely from git worktrees and always passes `-Pgit.root=<repo-root>` to avoid `nebula.release`/`grgit` failures like `.../config (Is a directory)`.
- If a Gradle-based packet lists `./gradlew test --tests ...`, execute the same arguments via `./.codex-gradle-test.sh` instead.
