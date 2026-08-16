# Agent Skills Repository

This repository contains reusable Codex skills and supporting tools for Jira planning, Dynatrace investigations, Jenkins pipeline diagnostics, service discovery, code review, and coordinated multi-repository implementation.

The tracked files are environment-neutral. Instance URLs, credentials, and local repository paths belong in the ignored root `.env` file and are loaded at runtime.

## Included components

| Directory | Purpose |
| --- | --- |
| `jira-assistant/` | Reads, searches, summarizes, and grooms Jira work using repository evidence and an approval-first workflow for writes. |
| `dtctl/` | Investigates Dynatrace logs with bounded, read-only DQL queries and scan-cost guardrails. |
| `jenkins-pipeline-checker/` | Inspects Jenkins pipeline runs, stage results, and logs through the Jenkins APIs. |
| `one-shot-this/` | Implements an approved single-repository Jira change in the current session, or launches isolated Codex workers in tmux-backed Git worktrees for a multi-repository change. |
| `service-catalog-mcp/` | Provides MCP tools that discover local services from their `service_description.md` files. |
| `generate-service-description/` | Generates or refreshes concise, evidence-based `service_description.md` files for repositories. |
| `code-review/` | Reviews GitHub pull requests and publishes only user-approved, actionable inline comments. |

`one-shot-this` composes the other capabilities: it reads the executable contract from Jira, uses service descriptions and the catalog to identify affected repositories, preserves requirements in implementation packets and GitHub pull requests, and routes Jenkins-backed checks through the pipeline checker. Single-repository plans stay in the current session; only multi-repository plans start workers.

## Shared delivery contract

The skills are designed as one evidence chain:

1. `generate-service-description` records repository purpose, integrations, change coupling, and a `Last verified` date.
2. `service-catalog-mcp` exposes that description and verification date for impact analysis.
3. `jira-assistant` turns current repository evidence into an approved Jira contract with acceptance criteria, validation, observability, rollout, and dependency links.
4. `one-shot-this` carries the full Jira URL and contract into each repository plan, work packet, branch, and draft PR.
5. GitHub checks index CI. `jenkins-pipeline-checker` follows Jenkins-backed checks to the failing stage and returns a reusable evidence block with the run URL.
6. When runtime or deployment verification requires logs, `dtctl` performs bounded, read-only Dynatrace investigation and returns the target and time window as evidence.
7. The PR URL is linked back to Jira, and Jira status is reconciled against PR, CI, deployment, and operational evidence rather than code presence alone.

Handoffs should preserve source URLs instead of copying large external records. A Jira-backed PR must include the full Jira ticket URL; a Jira update for PR-backed work must include the PR URL.

## Repository layout

Each skill directory contains a `SKILL.md` entrypoint plus any scripts, references, or agent metadata it needs. The service catalog is a standalone TypeScript MCP server with its own package and setup instructions.

```text
.
├── jira-assistant/
├── dtctl/
├── jenkins-pipeline-checker/
├── one-shot-this/
├── code-review/
├── service-catalog-mcp/
└── generate-service-description/
```

## Environment configuration

Create a root `.env` file for local values. It is excluded by `.gitignore` and must never be committed.

```dotenv
JIRA_BASE_URL=https://jira.example.com
JENKINS_BASE_URL=https://jenkins.example.com
JENKINS_USERNAME=myname@gmail.com
JENKINS_API_TOKEN=replace-with-a-local-secret
SERVICE_CATALOG_PATHS=/home/alex/projects/example-api:/home/alex/projects/example-worker
```

`SERVICE_CATALOG_PATHS` uses `:` between paths on macOS and Linux and `;` on Windows. The Jenkins skill also accepts the optional `JENKINS_ORG` variable. `one-shot-this` accepts optional `WORKSPACE_ROOT` and `BASE_BRANCH` overrides.

Load the variables into the current shell before running tools:

```bash
set -a
source .env
set +a
```

Configure Jira authentication through the Jira client or connector used by Codex. Keep all authentication material outside tracked files.

## Using the skills

Install a skill by copying or linking its directory into the Codex skills directory:

```bash
mkdir -p ~/.codex/skills
ln -s /absolute/path/to/this-repository/jira-assistant ~/.codex/skills/jira-assistant
ln -s /absolute/path/to/this-repository/dtctl ~/.codex/skills/dtctl
ln -s /absolute/path/to/this-repository/jenkins-pipeline-checker ~/.codex/skills/jenkins-pipeline-checker
ln -s /absolute/path/to/this-repository/one-shot-this ~/.codex/skills/one-shot-this
ln -s /absolute/path/to/this-repository/generate-service-description ~/.codex/skills/generate-service-description
ln -s /absolute/path/to/this-repository/code-review ~/.codex/skills/code-review
```

Restart or reload Codex after adding a skill so it can discover the new `SKILL.md`.

The multi-repository worker workflow additionally requires Git, Python 3, tmux, the Codex CLI, Jira access, and the service-catalog MCP server.

## Service catalog setup

Build and register the MCP server:

```bash
cd service-catalog-mcp
npm ci
npm run build
codex mcp add service-catalog -- node /absolute/path/to/service-catalog-mcp/dist/index.js
```

Every path configured through `SERVICE_CATALOG_PATHS` should point to a repository with a root `service_description.md`. See [`service-catalog-mcp/README.md`](service-catalog-mcp/README.md) for the server's tools and development commands.

## Safety and contribution notes

- Keep organization-specific names, URLs, credentials, and machine paths in `.env`, never in tracked examples.
- Treat Jira inspection as read-only until a proposed write plan is explicitly approved.
- Review generated multi-repository plans before spawning workers.
- Run the component-specific validation after changing a skill or server: validate each skill with the canonical `quick_validate.py`, run `python3 -m unittest one-shot-this/scripts/test_write_work_packets.py`, and run `npm test` in `service-catalog-mcp/`.
