---
name: generate-service-description
description: Generate or refresh a concise repo-level `service_description.md` by inspecting the codebase, runtime configuration, APIs, jobs, and integrations. Use when asked to create, update, validate, or improve a `service_description.md`, or when a repository needs a short service explainer that helps Codex and developers decide whether the repo is in scope for a change.
---

# Generate Service Description

## Overview

Generate or refresh a short, high-signal `service_description.md` for an application or service repository.
Base the document on local evidence from the repo rather than assumptions, and optimize for discovery, impact analysis, and fast triage.
When a repo already has `service_description.md`, treat it as a maintained document: remove stale claims, update changed behavior, and preserve accurate content that still matches the code.

## Workflow

1. Inspect any existing `service_description.md` first.
- Read the current file before sampling the codebase.
- Treat it as the baseline document to reconcile against current code and config, not as ground truth.
- For each existing section or claim, decide whether it should be kept, updated, shortened, or removed.
- Preserve useful structure and wording when it is still accurate; do not rewrite unchanged content just to rephrase it.

2. Establish the service shape from obvious entry points.
- Read `README*`, `build.gradle*`, `settings.gradle*`, `pom.xml`, `Dockerfile*`, `application*.yml`, `application*.yaml`, and deployment/config files that reveal runtime, framework, ports, auth, topics, or external clients.
- Identify the language/framework, service name, base path, and whether the repo is API-only, worker-only, or mixed.

3. Map the public surface area.
- Inspect controllers, routers, GraphQL schemas, consumers, schedulers, and CLIs.
- Capture only the route families, event consumers/producers, job names, or command entry points that materially define what the service does.
- Prefer grouped summaries over exhaustive endpoint dumps.

4. Identify core ownership and data flow.
- Determine the main entities, workflows, and storage systems the service owns.
- Trace the high-level request or event flow from ingress to persistence to downstream publication.
- Call out the behavior that explains why the repo exists, not low-level implementation details.

5. Capture integrations and coupling.
- List significant downstream/upstream systems and why they are called.
- Include queues, topics, databases, search indexes, auth providers, and major internal dependencies when they shape change impact.
- Note likely cross-repo impact only when there is concrete evidence.
- Capture repository, CI pipeline, and Jira ownership identifiers only when they are explicit in tracked configuration or documentation. These identifiers help downstream planning skills connect code, pull requests, build evidence, and Jira without guessing.

6. Draft or refresh `service_description.md`.
- Write for future discovery agents and developers, not end users.
- Keep the document concise, behavior-focused, and easy to scan.
- Use the section rubric in [references/service-description-rubric.md](./references/service-description-rubric.md).
- Always include `Last verified: YYYY-MM-DD` directly below the document title.
- If an existing file is present, update it in place when possible:
  - remove stale facts that no longer match the repo,
  - replace claims that have changed with current behavior,
  - keep accurate sections intact unless a rewrite materially improves clarity.

7. Verify against the repo.
- Re-read the most important code/config sources and remove anything that is speculative.
- Ensure no removed feature, endpoint family, job, or integration remains in the final file.
- Set `Last verified: YYYY-MM-DD` to the current review date every time the file is created or refreshed.
- Prefer omission over uncertain claims.

## Heuristics

- Prefer evidence from code and config over naming guesses.
- When updating an existing file, make the smallest set of edits that brings it back in sync with the code.
- Prefer route families, jobs, and integrations over file-by-file implementation notes.
- Keep the purpose statement understandable in one paragraph.
- Keep ownership boundaries explicit: what this service owns, and what it delegates.
- Mention operational behavior only when it changes how the service should be modified or debugged.
- Avoid copying long config blocks, schema files, or controller listings verbatim.

## Fast Source Checklist

- Existing `service_description.md` files in sibling repos for style calibration
- Existing repo-local `service_description.md` for claims to verify, preserve, or remove
- `README*`
- `build.gradle*`, `pom.xml`, `settings.gradle*`
- `src/main/resources/application*.yml`
- controller/router packages
- client/integration packages
- scheduler/job/consumer/listener packages
- persistence/repository/model packages
- infra manifests only if they reveal public behavior or dependencies

## Output Rules

- Write or update exactly one repo-local `service_description.md` unless the user asks for more.
- If `service_description.md` already exists, reconcile it with the current repo instead of discarding the whole file by default.
- Remove stale claims that are no longer supported by the code or config.
- Preserve accurate sections, headings, and wording when they still reflect the repo.
- Always include a `Last verified: YYYY-MM-DD` line directly below the title.
- When refreshing an existing file, replace any prior verification date with the current review date instead of leaving it stale.
- Keep the document short enough to read in a few minutes.
- Favor headings and grouped bullets over dense prose.
- Include a maintenance section that says when the document should be updated.
- If the repo is not actually a service, adapt the title and purpose to the real unit of ownership instead of forcing microservice language.

## Handoff to planning skills

- Treat `service_description.md` as the discovery index used by the service catalog, not as a substitute for inspecting code.
- Make `What usually changes together` concrete enough for Jira and implementation skills to identify cross-repository work.
- Include stable CI job or Jira project identifiers only when repository evidence supports them; never invent names from the repository basename.
- After a relevant architecture, API, job, integration, configuration, or operational change, refresh this file in the same code change so future Jira and implementation planning starts from current evidence.

## Reference

Read [references/service-description-rubric.md](./references/service-description-rubric.md) when drafting the document. It contains:
- a compact section template,
- guidance on what to include or skip,
- and a short checklist for keeping the document routing-focused rather than encyclopedic.
