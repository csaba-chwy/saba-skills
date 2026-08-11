# one-shot-this

`one-shot-this` turns an approved Jira issue into isolated, per-repository Codex workspaces. It reads the issue, discovers affected services, prepares a reviewable plan, and starts one tmux-backed worker per repository in a separate Git worktree.

## Prerequisites

- Git, Python 3, tmux, and the Codex CLI
- Jira and service-catalog MCP access
- A local workspace containing the target repositories
- A Git remote named `origin` for every target repository
- GitHub CLI (`gh`) already authenticated if workers should create draft PRs

Configure GitHub CLI yourself before starting a run:

```bash
gh auth login -h github.com
gh auth status -h github.com
```

Workers never run this login command, provide credentials, or attempt to authenticate for you.

The Codex command sandbox may not be able to reach `api.github.com`. This is separate from GitHub authentication: when a worker gets an API-connectivity error, it requests normal network access and retries `gh auth status` before deciding that login is required. Do not add a GitHub token to this repository's `.env` file.

## Workflow

1. Supply a Jira issue key.
2. Review the generated repository plan and approve worker spawning.
3. The launcher creates a worktree and branch for each repository, then opens one Codex worker per tmux pane.
4. Each worker implements its packet, runs the specified tests, and creates logical commits.
5. Each worker pushes its branch to `origin` with upstream tracking.
6. If `gh auth status -h github.com` succeeds, the worker opens a draft PR against `${BASE_BRANCH:-main}`. Otherwise, it reports the already-pushed branch and the login command you need to run.

The initial approval authorizes these worker actions. No second push/PR approval is requested.

## Environment

- `WORKSPACE_ROOT`: parent directory containing local repository clones. Defaults to the current directory.
- `BASE_BRANCH`: base revision for worktrees and draft PRs. Defaults to `main`.

## Use

Install or link this skill into the Codex skills directory, then invoke it explicitly with a Jira issue key. After the workers start, attach to the session shown by the launcher:

```bash
tmux attach -t codex-<JIRA_KEY>
```

Workers report their branch, commit SHA, push result, draft-PR URL when available, tests, and follow-ups. A failure to create a PR never undoes a successful branch push.
