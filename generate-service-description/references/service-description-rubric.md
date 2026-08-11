# Service Description Rubric

Use this rubric to draft or refresh a repository's `service_description.md`.

When the file already exists, treat the current document as a baseline to reconcile with the latest code state rather than starting from a blank page.

## Target Outcome

Produce a concise explainer that helps a future agent or developer answer:
- What does this repo/service do?
- Is this repo in scope for the task?
- Which APIs, jobs, stores, and integrations matter?
- What other systems are likely affected by a change here?

## Recommended Structure

Keep only the sections supported by the repo. Reorder or drop sections if needed.

```md
# <Service Name> Service Description

Last verified: YYYY-MM-DD

## Why this document exists
- Explain that this file is for discovery and impact analysis.
- Distinguish it from `AGENTS.md` if that file exists.

## Service in one paragraph
- Summarize the runtime role, primary inputs, and main outputs.

## Primary entry points
- HTTP route families, GraphQL entry points, event consumers, schedulers, or CLIs.

## What this service owns
- Main entities, workflows, or responsibilities.

## Core runtime flow
1. Describe the major request or event path.
2. Include only the steps that matter for reasoning about change impact.

## Downstream systems and purpose
- Name significant integrations and why they are called.

## Internal modules to read first
- Point to a few high-value packages/files when useful.

## Reliability or edge behavior
- Capture fallbacks, retries, degradation, or runtime flags only when behaviorally important.

## What usually changes together
- Note concrete cross-repo or cross-module coupling.

## How to keep this document evolving
- State which kinds of changes require updating the file.
```

## Inclusion Rules

- Prefer grouped summaries over full endpoint inventories.
- Prefer behavior and ownership over implementation trivia.
- Include auth, topics, caches, indexes, jobs, or feature flags only if they affect change planning.
- Include exact endpoint paths when they are part of the public contract.
- Always include a `Last verified: YYYY-MM-DD` line directly below the title.

## Exclusion Rules

- Do not paste large code snippets or config blocks.
- Do not restate every class name in the repo.
- Do not speculate about consumers or dependencies without evidence.
- Do not turn the file into runbook or onboarding documentation.
- Do not duplicate `README` content unless it directly supports scope/impact analysis.

## Repo Evidence To Sample

- Build files and dependency manifests
- Application config
- Controllers/routers/GraphQL schemas
- Background jobs, consumers, and schedulers
- Clients/integration layers
- Repository/model packages
- Existing `service_description.md` files in neighboring repos for tone and structure

## Editing Existing Files

- Read the existing file before inspecting the repo in detail.
- Evaluate each section and claim as `keep`, `update`, or `remove` based on current code and config.
- Preserve accurate sections that already help routing or triage.
- Keep existing headings, ordering, and phrasing when they are still accurate and useful.
- Replace generic statements like "handles business logic" with concrete responsibilities.
- Refresh stale dates, dependency names, endpoint families, and migration notes.
- Delete statements about removed endpoints, integrations, jobs, or ownership that no longer exist.
- If only part of a section is stale, edit that portion instead of rewriting the whole section unless clarity would suffer.
- Ensure the file has exactly one `Last verified: YYYY-MM-DD` line near the top and update it to the current review date whenever the document is revalidated.
- Keep the file shorter than the amount of code it points to; it is an index, not a substitute for reading the source.
