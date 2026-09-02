# Complete Saba Skills setup

This guide installs and configures every skill in this repository. It also sets up the service-catalog MCP server used by `one-shot-this`.

## 1. Prerequisites

Install and authenticate the tools below before using the skills that depend on them.

| Tool | Used by | Setup |
| --- | --- | --- |
| Codex | all skills | Install the Codex CLI and restart/reload Codex after linking skills. |
| Git | `one-shot-this`, `code-review`, service-description work | Configure access to the local repositories you intend to inspect or change. |
| GitHub CLI (`gh`) | `one-shot-this`, `code-review` | Run `gh auth login -h github.com`, then `gh auth status -h github.com`. Do not put a GitHub token in `.env`. |
| Jira CLI (`jira`) | `jira-assistant`, `one-shot-this` | Configure it with your Jira account. Its credentials/configuration are managed by the CLI, not this repository. |
| Node.js and npm | `service-catalog-mcp` | Use a current Node.js version compatible with the package lockfile, then run `npm ci`. |
| Python 3 | `dtctl`, `generate-service-description`, `one-shot-this` | Ensure `python3` is on `PATH`. |
| tmux | multi-repository `one-shot-this` work | Required only when a plan affects two or more repositories. |
| Dynatrace `dtctl` | `dtctl` | Install `dtctl`; authenticate through its browser-based OAuth flow below. |
| AWS CLI, kubectl, and Helm | `helm` | Configure AWS SSO and Kubernetes contexts for each environment you will diagnose. |

## 2. Create the local environment file

The root `.env` is gitignored. Create it locally and replace every placeholder appropriate to your environment. Values in this file are loaded only into the shell that starts Codex or the MCP server.

```dotenv
# Jira: documentation/context only. Jira CLI authentication is configured separately.
JIRA_BASE_URL=https://jira.example.com

# Jenkins Pipeline Checker
JENKINS_NONPROD_BASE_URL=https://jenkins-nonprod.example.com
JENKINS_PROD_BASE_URL=https://jenkins.example.com
JENKINS_USERNAME=your.name@example.com
JENKINS_API_TOKEN=store-your-jenkins-api-token-here
JENKINS_ORG=jenkins

# Dynatrace dtctl: tenant URLs only; do not set platform tokens here.
DTCTL_NONPROD_ENVIRONMENT=https://your-nonprod.apps.dynatrace.com
DTCTL_PROD_ENVIRONMENT=https://your-prod.apps.dynatrace.com

# Service Catalog MCP: absolute local repository paths, separated by : on macOS/Linux
# (use ; on Windows).
SERVICE_CATALOG_PATHS=/absolute/path/to/service-a:/absolute/path/to/service-b

# one-shot-this defaults; both are optional.
WORKSPACE_ROOT=/absolute/path/to/your/local-repositories
BASE_BRANCH=main

# Optional multi-repository Gradle cache location. Normally the launcher sets this itself.
# CODEX_SHARED_GRADLE_USER_HOME=/absolute/path/to/your/local-repositories/.gradle-user-home
```

Load it before running shell tools or launching the service catalog:

```bash
set -a
source /absolute/path/to/saba-skills/.env
set +a
```

Never commit `.env`, OAuth credentials, Jira credentials, Jenkins tokens, or GitHub tokens.

## 3. Install every Codex skill

Link each directory that contains a `SKILL.md` into the Codex skills directory:

```bash
SKILLS_REPO=/absolute/path/to/saba-skills
mkdir -p ~/.codex/skills

ln -s "$SKILLS_REPO/code-review" ~/.codex/skills/code-review
ln -s "$SKILLS_REPO/dtctl" ~/.codex/skills/dtctl
ln -s "$SKILLS_REPO/generate-service-description" ~/.codex/skills/generate-service-description
ln -s "$SKILLS_REPO/helm" ~/.codex/skills/helm
ln -s "$SKILLS_REPO/jenkins-pipeline-checker" ~/.codex/skills/jenkins-pipeline-checker
ln -s "$SKILLS_REPO/jira-assistant" ~/.codex/skills/jira-assistant
ln -s "$SKILLS_REPO/one-shot-this" ~/.codex/skills/one-shot-this
```

Restart or reload Codex after creating the links. The service catalog is an MCP server, not a skill directory; set it up in the next section.

## 4. Build and register the service catalog

`one-shot-this` uses this server to locate repositories from their root `service_description.md` files.

```bash
cd /absolute/path/to/saba-skills/service-catalog-mcp
npm ci
npm run build
codex mcp add service-catalog -- node "$(pwd)/dist/index.js"
```

Configure `SERVICE_CATALOG_PATHS` in `.env` with absolute repository paths. Every configured repository needs a root `service_description.md`; use `generate-service-description` to create or refresh one when necessary. Restart/reload Codex after registering the MCP server.

## 5. Configure the authenticated integrations

### Jira (`jira-assistant` and `one-shot-this`)

Authenticate and configure the `jira` CLI according to your organization’s Jira CLI setup, then confirm the active identity:

```bash
jira me
```

`JIRA_BASE_URL` records the tenant URL for shared context; it does not replace Jira CLI authentication.

### Jenkins (`jenkins-pipeline-checker`)

Create a Jenkins API token from your Jenkins user security page. Set `JENKINS_NONPROD_BASE_URL`, `JENKINS_PROD_BASE_URL`, `JENKINS_USERNAME`, and `JENKINS_API_TOKEN` in `.env`; `JENKINS_ORG` is optional and defaults to `jenkins`. GitHub links always attach to nonproduction Jenkins pipelines, so use `JENKINS_NONPROD_BASE_URL` for GitHub-linked checks. A full Blue Ocean URL may be used directly and preserves the environment encoded in the link.

### Dynatrace (`dtctl`)

Set both Dynatrace environment URL variables in `.env`. They must be HTTPS tenant URLs, not tokens. Establish separate read-only OAuth contexts:

```bash
dtctl auth login --context nonprod --environment "$DTCTL_NONPROD_ENVIRONMENT" --safety-level readonly
dtctl auth login --context prod --environment "$DTCTL_PROD_ENVIRONMENT" --safety-level readonly
```

Use `DT_CONTEXT` only as a short-lived command selector; it is not required in `.env`:

```bash
DT_CONTEXT=nonprod # use prod only for prd
dtctl config describe-context "$DT_CONTEXT" --plain
dtctl --context "$DT_CONTEXT" auth status --plain
```

Keep the `prod` context read-only. Do not export, print, or commit stored OAuth credentials.

### Kubernetes and Helm (`helm`)

`helm` has no persistent repository-specific environment variable. Before querying an EKS-backed context, authenticate with the environment-matched AWS SSO profile:

```bash
aws sso login --profile stg
aws sts get-caller-identity --profile stg
AWS_PROFILE=stg kubectl config get-contexts -o name
```

Use `AWS_PROFILE` per command and keep it matched to the selected `prd`, `stg`, `qat`, or `dev` environment. Confirm the Kubernetes context before investigating. The skill is read-only unless a change is explicitly approved.

## 6. Optional one-shot-this worker settings

`WORKSPACE_ROOT` defaults to the current directory and `BASE_BRANCH` defaults to `main`. Multi-repository runs additionally require Git, Python 3, tmux, Codex CLI, configured Jira/service-catalog access, an `origin` remote for every target repository, and authenticated GitHub CLI access.

The worker launcher sets `CODEX_SHARED_GRADLE_USER_HOME` to `$WORKSPACE_ROOT/.gradle-user-home` unless you override it. The generated Gradle wrapper converts it to `GRADLE_USER_HOME`; neither needs to be set for normal use.

## 7. Verify the repository setup

Run the component checks after setup or after modifying a component:

```bash
python3 -m unittest one-shot-this/scripts/test_write_work_packets.py
cd /absolute/path/to/saba-skills/service-catalog-mcp && npm test
```

For skill-content validation, run each skill’s canonical `quick_validate.py` when present. You can also confirm the installed Codex symlinks and the MCP registration with your local Codex configuration.

## Environment-variable reference

| Variable | Required by | Purpose | Where to set it |
| --- | --- | --- | --- |
| `JIRA_BASE_URL` | repository-wide context | Jira tenant URL; does not authenticate the Jira CLI | `.env` |
| `JENKINS_NONPROD_BASE_URL` | `jenkins-pipeline-checker` | Nonproduction Jenkins instance URL; used for GitHub PR/check links | `.env` |
| `JENKINS_PROD_BASE_URL` | `jenkins-pipeline-checker` | Production Jenkins instance URL | `.env` |
| `JENKINS_USERNAME` | `jenkins-pipeline-checker` | Jenkins API username | `.env` |
| `JENKINS_API_TOKEN` | `jenkins-pipeline-checker` | Jenkins API token | `.env` |
| `JENKINS_ORG` | `jenkins-pipeline-checker` | Blue Ocean organization; defaults to `jenkins` | optional `.env` |
| `DTCTL_NONPROD_ENVIRONMENT` | `dtctl` | Nonproduction Dynatrace HTTPS tenant URL | `.env` |
| `DTCTL_PROD_ENVIRONMENT` | `dtctl` | Production Dynatrace HTTPS tenant URL | `.env` |
| `DT_CONTEXT` | `dtctl` commands | Selects `nonprod` or `prod` context for one command/session | command shell |
| `SERVICE_CATALOG_PATHS` | `service-catalog-mcp` | Absolute service-repository paths | `.env` |
| `WORKSPACE_ROOT` | `one-shot-this` | Parent local-repository directory | optional `.env` |
| `BASE_BRANCH` | `one-shot-this` | Base branch for worktrees and draft PRs; defaults to `main` | optional `.env` |
| `AWS_PROFILE` | `helm` commands | AWS SSO profile matched to selected environment | command shell |
| `CODEX_SHARED_GRADLE_USER_HOME` | `one-shot-this` generated Gradle wrapper | Shared Gradle cache; normally launcher-managed | optional command shell |
| `GRADLE_USER_HOME` | generated Gradle wrapper | Gradle cache derived from `CODEX_SHARED_GRADLE_USER_HOME` | launcher-managed |
