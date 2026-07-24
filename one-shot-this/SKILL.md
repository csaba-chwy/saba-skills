---
name: one-shot-this
description: |
  Explicit skill. Given a Jira issue key, fetch requirements via Jira MCP, identify impacted repos via service-catalog MCP,
  produce a per-repo implementation plan, ask for approval, then spawn one Codex worker per repo in tmux panes using git worktrees.
---

# Workflow (must follow exactly)

## Inputs
- Jira story key (e.g., DEMO-123)
- Environment variables (if set):
  - WORKSPACE_ROOT: folder that contains local clones of repos (default: current directory)
  - BASE_BRANCH: default base branch for worktrees (default: main)

## Step 1 — Requirements intake (read-only)
1) Use Jira MCP to fetch:
   - title, description, acceptance criteria, links, attachments
2) Summarize requirements and list assumptions/questions.

## Step 2 — Repo selection using service catalog (read-only)
1) Use service-catalog MCP to find impacted repos/services.
2) Produce a list of repos with:
   - why impacted
   - key modules/files likely touched
   - integration/dependency notes

## Step 3 — Plan
Output a structured plan with:
- jira_key
- issue_type and/or title when known, so branch type can be inferred
- repos: list of { name, local_path (if known), branch_suffix, branch_type (optional), steps[], tests[], rollout_notes }
- cross_repo_steps (if any)
Then ask for approval:
"Approve to generate work packets + spawn tmux workers?"

STOP if not approved.

## Step 4 — Generate work packets + spawn tmux workers
1) Run scripts/write_work_packets.py to write one markdown packet per repo into ./run/packets/
2) Run scripts/spawn_tmux_worktrees.sh to:
   - create a worktree per repo
   - open a tmux session with one pane per repo
   - start a Codex session in each pane, feeding it the repo’s packet
   - note: the launcher canonicalizes `<plan.json>` and `<packets_dir>` to absolute paths, so callers can pass relative paths safely
3) After spawn succeeds, do not run extra tmux verification commands.
4) Final response for this step must be a single instruction line:
   - `tmux attach -t codex-<JIRA_KEY>`

## Worker rules (each spawned Codex session)
- Operate only within its repo/worktree.
- Implement per packet.
- Run tests listed in the packet.
- Branch naming defaults to `feature/<branch_suffix>`. Use `bugfix/<branch_suffix>` only when the story explicitly indicates a bug fix or the plan sets `branch_type: bugfix`.
- Before any push or PR, explicitly ask:
  "Approve push + PR for <repo>?"
- If approved:
  - ensure the current local branch tracks `origin/<current-branch>` (do not only check that some upstream exists)
  - if tracking is missing or points elsewhere (for example `origin/main`), set/fix it by pushing with upstream tracking (for example `git push -u origin <branch>`)
  - create PR (prefer gh; otherwise print the exact manual command)
- Report back with:
  - branch name
  - PR link
  - tests run + results
  - any follow-ups/risks

## Gradle worktree reliability (Nebula/Grgit)
- Only for repos that use Gradle, run Gradle tests in spawned worktrees via `./.codex-gradle-test.sh`.
- The launcher only copies this wrapper when the worktree contains `./gradlew`.
- The launcher uses `${SHELL}` when present instead of assuming Bash.
- Gradle worktrees should use the user's normal Gradle configuration from `~/.gradle` by default.
- A workspace-local Gradle configuration may override the default when the launched workspace intentionally provides one.
- This wrapper exists to make Gradle run safely from git worktrees and always passes `-Pgit.root=<repo-root>` to avoid `nebula.release`/`grgit` failures like `.../config (Is a directory)`.
- If a Gradle-based packet lists `./gradlew test --tests ...`, execute the same arguments via `./.codex-gradle-test.sh` instead.
