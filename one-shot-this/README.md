# one-shot-this

`one-shot-this` turns an approved Jira issue into an implementation that preserves the Jira contract through code, GitHub, and CI. Single-repository changes stay in the current Codex session; multi-repository changes use one isolated tmux-backed Git worktree per repository.

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
2. Review the generated repository plan and approve implementation, commits, push, draft PR, and Jira link-back.
3. For one repository, continue in the current session. For multiple repositories, create a worktree and Codex worker per repository.
4. The current session or each worker implements its approved scope, runs the specified tests, and creates logical commits.
5. Each implementation branch is pushed to `origin` with upstream tracking.
6. If `gh auth status -h github.com` succeeds, open a draft PR against `${BASE_BRANCH:-main}` containing the full Jira URL, acceptance-criteria mapping, tests, observability, and rollout notes. Otherwise, report the already-pushed branch and the login command the user needs to run.
7. Link the PR URL back to Jira, inspect GitHub checks, and use the Jenkins or bounded read-only Dynatrace skill when those systems hold the relevant evidence.

The initial approval authorizes these actions. No second push/PR approval is requested unless the approved scope materially changes.

## Environment

- `WORKSPACE_ROOT`: parent directory containing local repository clones. Defaults to the current directory.
- `BASE_BRANCH`: base revision for worktrees and draft PRs. Defaults to `main`.

## Use

Install or link this skill into the Codex skills directory, then invoke it explicitly with a Jira issue key. For a multi-repository change, attach to the session shown by the launcher:

```bash
tmux attach -t codex-<JIRA_KEY>
```

Workers report their branch, commit SHA, push result, draft-PR URL when available, tests, and follow-ups. A failure to create a PR never undoes a successful branch push.
