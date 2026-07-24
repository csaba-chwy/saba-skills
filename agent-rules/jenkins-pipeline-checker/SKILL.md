---
name: jenkins-pipeline-checker
description: Check Jenkins pipeline runs and extract stage logs, errors, and summaries.
metadata:
  short-description: Jenkins pipeline checks
---

# Jenkins Pipeline Checker

Use this skill when a user asks to check Jenkins pipeline status or stage output.

## Prereqs

- `JENKINS_BASE_URL`, `JENKINS_USERNAME`, and `JENKINS_API_TOKEN` are already set in the environment.
- Default `JENKINS_ORG` is `jenkins`.

## Workflow

1) Confirm required env vars exist. If missing, ask the user for them.
2) Find the pipeline run:
   - For multibranch repos, the job is typically `build-<repo-name>` and the PR job name is `PR-<number>`.
   - Example Blue Ocean URL: `https://jenkins.example.com/blue/organizations/jenkins/build-<repo-name>/detail/PR-<number>/<run_id>/pipeline`.
3) Query the run summary via the Blue Ocean REST API.
4) List stage nodes and locate the relevant stage (ask if unclear).
5) Fetch the stage log and summarize:
   - Key log lines
   - Errors and warnings
6) Report status + key details; if auth fails, ask for correct Jenkins username or token type.
   - If the API returns HTML instead of JSON, it's usually an SSO/login page or invalid token; verify `JENKINS_USERNAME`, `JENKINS_API_TOKEN`, and `JENKINS_BASE_URL`.
   - For multibranch PR runs, Blue Ocean run endpoints can 404 unless you include branch context. Prefer the Jenkins Pipeline REST API (wfapi) as the default for PR runs:
     - From `.../detail/PR-264/3/pipeline`, the classic job path is `/job/<pipeline>/job/PR-264/3/`.
     - Stage list (JSON): `/job/<pipeline>/job/PR-264/3/wfapi/describe`
     - Stage log (may be empty for some stages): `/job/<pipeline>/job/PR-264/3/execution/node/<id>/wfapi/log?start=0`
     - Full log (reliable fallback): `/job/<pipeline>/job/PR-264/3/consoleText`

## Best Defaults

- Read `JENKINS_BASE_URL` from the environment and assume `JENKINS_ORG=jenkins` unless told otherwise.
- For PR runs, use wfapi endpoints first; fall back to `consoleText` if stage logs are empty.
- When given a Blue Ocean URL, derive the classic job path as `/job/<pipeline>/job/<branch>/ <run_id>/` (e.g., `PR-264`).

## Scripts

- `scripts/check_pipeline_stage.sh`
  - Usage: `check_pipeline_stage.sh <pipeline> <run_id> <stage_name> [branch_name]`
  - Alternate: `check_pipeline_stage.sh <blue_ocean_url> <stage_name>`
  - Prints stage log to stdout; use grep to summarize.
