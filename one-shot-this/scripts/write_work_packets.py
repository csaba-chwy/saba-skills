#!/usr/bin/env python3
import json, os, re, sys
from pathlib import Path

TEMPLATE = """# Work Packet: {repo}

## Context
- Jira: {jira_key}
- Repo: {repo}
- Branch: {branch}

## Objective
Implement the approved plan for this repo only.

## Steps
{steps}

## Tests to run
{tests}

## Build tool note
{build_tool_note}

## Push and PR note
- Commit the completed implementation before publishing it. A pushed branch and draft PR cannot include uncommitted changes.
- Push the current branch and establish `origin/<current-branch>` tracking:
  - `branch="$(git branch --show-current)"`
  - `git push -u origin "$branch"`
- Never run `gh auth login`, provide credentials, or otherwise authenticate on the user's behalf.
- After the push, run `gh auth status -h github.com` using network access that can reach `api.github.com`.
  - If a restricted environment cannot reach GitHub's API, request normal network access and retry the status check. Do not mistake an API-connectivity failure for an invalid login, and never run `gh auth login` yourself.
  - If it fails after GitHub API access is available, report: `GitHub CLI is not authenticated. Run gh auth login -h github.com, then create a draft PR from <branch>.` Stop after reporting the pushed branch.
  - If it succeeds, write a temporary PR body with the Jira key plus a concise implementation and test summary. Create a non-interactive draft PR with `gh pr create --draft --base "${{BASE_BRANCH:-main}}" --head "$branch" --title "<JIRA_KEY>: <concise summary>" --body-file <path-to-body>`.
  - If PR creation fails, report the failure and leave the pushed branch intact. Do not retry authentication.

## Constraints
- Only change this repo/worktree.
- Keep commits small and logical.
- The approved work packet authorizes commits, a branch push, and an attempted draft PR.

## Definition of done
- Tests pass
- Branch pushed; draft PR opened and linked to Jira when GitHub CLI is already authenticated
- Summary posted back (PR link, changes, test results, follow-ups)
"""

def bullet(lines):
    if not lines:
        return "- (none)"
    return "\n".join([f"- {x}" for x in lines])

def build_tool_note(repo_config):
    if repo_config.get("build_tool") == "gradle":
        return "- This repo is marked as Gradle-based. In worktrees, run Gradle commands via `./.codex-gradle-test.sh` with the same args."
    return "- If this repo has a `./gradlew` wrapper in the spawned worktree, use `./.codex-gradle-test.sh` for Gradle commands. Otherwise use the repo's native test/build command."

def infer_branch_prefix(plan, repo_config):
    explicit_value = repo_config.get("branch_type") or plan.get("branch_type")
    if explicit_value:
        normalized = str(explicit_value).strip().lower()
        if normalized in {"bugfix", "bug", "fix", "hotfix"}:
            return "bugfix"
        if normalized in {"feature", "feat"}:
            return "feature"

    explicit_text = " ".join(
        str(value)
        for value in (
            repo_config.get("story_type"),
            plan.get("story_type"),
            plan.get("issue_type"),
            plan.get("title"),
            plan.get("summary"),
        )
        if value
    ).lower()
    if re.search(r"\b(bug|bugfix|fix|defect|hotfix|regression)\b", explicit_text):
        return "bugfix"
    return "feature"

def branch_name(plan, jira_key, repo_config):
    explicit_branch = repo_config.get("branch")
    if explicit_branch:
        return explicit_branch

    suffix = repo_config.get("branch_suffix") or f"{jira_key}-{repo_config['name']}".replace("/", "-")
    suffix = str(suffix).strip().lstrip("/")
    return f"{infer_branch_prefix(plan, repo_config)}/{suffix}"

def main():
    if len(sys.argv) < 3:
        print("Usage: write_work_packets.py <plan_json_path> <out_dir>", file=sys.stderr)
        sys.exit(2)

    plan_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = json.loads(plan_path.read_text())
    jira_key = plan.get("jira_key") or plan.get("issue") or "UNKNOWN"

    repos = plan.get("repos", [])
    if not repos:
        raise SystemExit("Plan JSON has no repos[]")

    for r in repos:
        repo = r["name"]
        branch = branch_name(plan, jira_key, r)
        steps = bullet(r.get("steps", []))
        tests = bullet(r.get("tests", []))
        content = TEMPLATE.format(
            jira_key=jira_key,
            repo=repo,
            branch=branch,
            steps=steps,
            tests=tests,
            build_tool_note=build_tool_note(r),
        )
        (out_dir / f"{repo.replace('/','-')}.md").write_text(content)

if __name__ == "__main__":
    main()
