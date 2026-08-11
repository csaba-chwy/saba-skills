#!/usr/bin/env python3
import json, re, sys
from pathlib import Path

TEMPLATE = """# Work Packet: {repo}

## Context
- Jira: [{jira_key}]({jira_url})
- Summary: {summary}
- Repo: {repo}
- Branch: {branch}

## Scope and boundaries
{description}

## Objective
{why_impacted}

## Acceptance criteria
{acceptance_criteria}

## Steps
{steps}

## Tests to run
{tests}

## Observability
{observability}

## Rollout notes
{rollout_notes}

## Cross-repository coordination
{cross_repo_steps}

## Dependency links
{dependency_links}

## Build tool note
{build_tool_note}

## Push and PR note
- Ask: `Approve push + draft PR + Jira link for {repo}?`
- When the user gives that approval, ensure the current local branch tracks `origin/<current-branch>`.
- Do not only check whether an upstream exists; it may exist but point to `origin/main` or `origin/master`.
- A safe generic sequence is:
  - `branch="$(git branch --show-current)"`
  - `upstream="$(git for-each-ref --format='%(upstream:short)' "refs/heads/$branch")"`
  - `if [[ "$upstream" != "origin/$branch" ]]; then git push -u origin "$branch"; fi`
- Open a draft PR whose description includes the full Jira URL `{jira_url}`, an acceptance-criteria mapping, tests, observability, and rollout notes.
- Link the PR URL back to Jira and read it back. Inspect GitHub checks; if one points to Jenkins, use `jenkins-pipeline-checker` and retain the Jenkins run URL in the result.

## Constraints
- Only change this repo/worktree.
- Keep commits small and logical.
- Do not push or create a PR without asking for approval in this session.

## Definition of done
- Tests pass
- Draft PR opened with the Jira contract and linked back to Jira
- Relevant GitHub/Jenkins checks inspected or their pending state reported
- Summary posted back (PR link, Jira link-back, changes, test and CI results, follow-ups)
"""

def bullet(lines):
    if not lines:
        return "- (none)"
    return "\n".join([f"- {x}" for x in lines])

def required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"Plan JSON requires non-empty {field}")
    return value.strip()

def required_list(value, field):
    if not isinstance(value, list) or not value:
        raise SystemExit(f"Plan JSON requires non-empty {field}[]")
    return value

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
    jira_key = required_text(plan.get("jira_key") or plan.get("issue"), "jira_key")
    jira_url = required_text(plan.get("jira_url"), "jira_url")
    if not re.match(r"^https?://", jira_url):
        raise SystemExit("Plan JSON jira_url must be an absolute HTTP(S) URL")
    summary = required_text(plan.get("summary") or plan.get("title"), "summary")
    description = required_text(plan.get("description"), "description")
    acceptance_criteria = required_list(plan.get("acceptance_criteria"), "acceptance_criteria")

    repos = plan.get("repos", [])
    if not repos:
        raise SystemExit("Plan JSON has no repos[]")

    for r in repos:
        repo = r["name"]
        branch = branch_name(plan, jira_key, r)
        repo_acceptance_criteria = r.get("acceptance_criteria") or acceptance_criteria
        steps = bullet(r.get("steps", []))
        tests = bullet(r.get("tests", []))
        content = TEMPLATE.format(
            jira_key=jira_key,
            jira_url=jira_url,
            summary=summary,
            description=description,
            repo=repo,
            branch=branch,
            why_impacted=required_text(r.get("why_impacted"), f"repos[{repo}].why_impacted"),
            acceptance_criteria=bullet(repo_acceptance_criteria),
            steps=steps,
            tests=tests,
            observability=bullet(r.get("observability", [])),
            rollout_notes=bullet(r.get("rollout_notes", [])),
            cross_repo_steps=bullet(plan.get("cross_repo_steps", [])),
            dependency_links=bullet(plan.get("dependency_links", [])),
            build_tool_note=build_tool_note(r),
        )
        (out_dir / f"{repo.replace('/','-')}.md").write_text(content)

if __name__ == "__main__":
    main()
