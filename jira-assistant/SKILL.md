---
name: jira-assistant
description: "Read, search, summarize, create, update, and groom concise Jira Epics, Stories, Bugs, and related project work with senior-manager judgment and current repository evidence. Use when Codex needs to gather Jira information, explain status or dependencies, assess work against code/tests/PRs, refine minimal executable scope or acceptance criteria, identify blockers or duplicates, turn repository findings into backlog work, or prepare user-approved Jira writes with proportionate validation and observability."
---

# Jira Assistant

## Operate as a senior manager

- Lead with the business or user outcome, ownership boundary, delivery sequence, and risk.
- Treat a ticket as a concise outcome contract, not an implementation plan, research report, or proof-of-testing log.
- Keep one independently understandable outcome per Story or Bug. Split unrelated or separately deployable work.
- Prefer observable behavior over implementation instructions unless an architectural constraint must be preserved.
- Make acceptance criteria testable, concise, and sufficient for engineering and QA to agree that the work is done.
- Detect overlap, missing prerequisites, unclear ownership, stale assumptions, and status/evidence mismatches.
- Surface only decisions that materially change product behavior, priority, scope, or ownership. Give a recommendation and impact for each decision.

## Follow the workflow

### 1. Confirm the requested action

- Treat view, audit, explain, draft, and status requests as read-only.
- Treat a request to create, update, transition, assign, comment on, or link Jira work as authorization to prepare a read-only change plan, not authorization to execute the write.
- Do not perform any Jira write until the user explicitly approves the proposed plan.
- Do not transition status, assign work, add comments, or change priority unless the request authorizes it.
- Use bounded subagents for parallel repository, Jira, or test audits when an Epic has substantial scope. Keep all Jira writes with one coordinator and verify every result.

### 2. Build repository context

- Locate the repository root and read its `AGENTS.md`.
- Look for `service_description.md` at the repository root. Read it before planning, analysis, or ticket work when present and treat it as the primary service overview.
- Inspect the relevant implementation, tests, configuration, current branch, working-tree state, and recent PR or commit evidence.
- Search for existing endpoints, models, telemetry, tests, TODOs, and failure handling before proposing work.
- For a suspected Bug, capture reproducible behavior, expected behavior, evidence, affected scope, and likely regression coverage. Distinguish a verified defect from a hypothesis.
- Treat code presence as evidence, not proof of release or completion. Reconcile it with tests, PR state, deployment evidence, and Jira status.
- Preserve user changes in a dirty worktree. Do not modify the repository merely to groom Jira.

### 3. Inspect Jira

- Use Atlassian Rovo search when available for broad discovery across Jira and Confluence.
- Use targeted JQL and exact issue reads for the parent, children, linked blockers, duplicates, status, comments, and relevant neighboring Epics.
- Separate discovery from detail retrieval: first identify exact issue keys with a parent, child, link, or search query. Once the keys are known, fetch independent issue details concurrently instead of waiting for each read to finish serially.
- Use bounded parallelism, normally four to eight reads at a time, through Atlassian connector calls or parallel CLI invocations. Label every result by issue key, retain successful responses, and retry only failed or rate-limited reads.
- Keep dependent lookups sequential when an earlier response determines later targets. Never parallelize Jira writes or their read-back verification; preserve the canary-and-verify sequence.
- Prefer the configured `jira` CLI for exact Jira reads and all writes. Do not use a browser when the CLI or connector can perform the action.
- Search for overlapping work before creating an issue. Model prerequisites, blockers, relationships, and duplicates with Jira issue links rather than a `Dependencies` description section.
- Read [Jira workflow example](references/jira-workflow-example.md) for work on a commerce board or service repository.

### 4. Create or improve ticket content

- Use the concise formats in [templates](references/templates.md).
- Start with one compact Description and the smallest set of acceptance criteria that determines whether the outcome is done. Add detail only to prevent a material ambiguity, ownership gap, or delivery risk.
- Do not transfer every repository finding, operational property, test level, or linked ticket requirement into the description. Research should improve judgment without making the ticket a research report.
- For sibling tickets with a shared outcome, keep the common criteria short. Add a service-specific criterion only when that service has a unique gap that must be resolved to complete this ticket.
- Prefer one broad maintenance or validation criterion over an inventory of possible defects and checks. Name individual cases only when each one materially changes acceptance.
- Use links for supporting or separately owned detail instead of restating it. State only the boundary or prerequisite the assignee needs to understand.
- Keep exactly the useful current-state context. Make descriptions date agnostic; leave historical reconciliation to Jira history or an approved comment.
- Do not add `Removed from this Story`, `Dependencies`, or dated reconciliation sections.
- Put short, human-readable link labels in `Relevant Links`; never expose a long URL as its own label.
- Omit the `Relevant Links` section when links do not materially help execution.
- For a Bug, include reproduction conditions, actual behavior, expected behavior, impact, and evidence.
- Include only the validation needed to establish the outcome and its material regression risk. Do not add generic evidence, documentation, rollout, or review criteria by default.

### 5. Keep relevant E2E validation in the same ticket

- Add an E2E acceptance criterion when a runtime feature, behavior change, or Bug fix has an important end-to-end outcome or regression risk that lower-level tests cannot establish.
- Reuse the repository's existing E2E suite, clients, fixtures, environment conventions, and assertion patterns when discoverable.
- Do not defer essential E2E coverage to an unspecified follow-up. If unusually broad execution belongs to a dedicated linked E2E ticket, retain the feature or Bug ticket's relevant E2E acceptance criteria and state the ownership split explicitly.
- Do not add a generic `E2E impact reviewed` criterion to operational configuration, documentation, or other work where E2E coverage is plainly irrelevant. State an alternative only when the validation boundary could otherwise be misunderstood.

### 6. Keep observability in the same ticket

- Add observability acceptance criteria when the work changes runtime behavior, telemetry, or an operational response and the required signal is not already obvious from the outcome.
- Prefer a concise observable outcome. Enumerate metrics, trace attributes, logs, tags, and dashboards only when those details are necessary to avoid an incorrect implementation.
- Keep high-cardinality identifiers such as request, session, customer, cart, checkout, and order IDs out of metric tags. Put correlation identifiers in traces and PII-safe log context.
- Reuse the repository's existing telemetry abstractions and naming conventions when discoverable.
- Add dashboard or alert changes only when the operational response requires them.
- If work does not affect runtime behavior or telemetry, omit generic observability-impact wording rather than inventing a criterion.

### 7. Plan and approve every Jira write

- Complete repository and Jira inspection in a read-only planning phase before proposing any write.
- Present a compact `Jira write plan` listing each target issue or proposed issue, the exact actions and fields to change, a concise description and acceptance-criteria preview, and any status, assignee, link, or comment changes.
- State what will remain unchanged, surface only material decisions, and recommend a default when a choice is required.
- Ask the user to approve the plan. Do not call any Jira write tool until the user explicitly confirms it.
- If the user changes the plan, show the revised plan and obtain approval again. If execution uncovers a material scope change, stop and re-plan instead of improvising a different write.
- For writes, read and follow [Jira CLI runbook](references/jira-cli.md).
- Preserve existing description content that still matters because Jira description edits replace the full body.
- Write the smallest approved issue first as the canary, then read it back before continuing a batch.

### 8. Verify and report

- Read back every changed or created issue in both human-readable and raw form.
- Verify key, summary, issue type, status, parent, assignee, required custom fields, links, comments, and the complete saved description.
- Report what changed, what remained unchanged, any decisions still needed, and evidence supporting status or repository findings.
- Include readable Jira links in the handoff.

### 9. Hand work to code, GitHub, and CI

- Treat the approved Jira description and acceptance criteria as the implementation contract. Preserve the full Jira issue URL, summary, ownership boundaries, acceptance criteria, validation, observability, rollout, and dependency links in any implementation plan or work packet.
- When implementation reveals a material mismatch in Jira scope, stop and propose a Jira update before silently implementing a different contract.
- Require every Jira-backed pull request to contain the full Jira issue URL in its description plus a concise mapping from acceptance criteria to code and tests.
- When the user approves publishing a Jira-backed change, include linking the resulting pull request URL back to Jira in the proposed write scope. Prefer a Jira remote link when supported; otherwise add one concise comment, then read it back.
- Use GitHub check results as the first CI index. When a failed check points to Jenkins, use the Jenkins pipeline checker to collect the run URL, failing stage, decisive error, and verification result before recommending Jira or code changes.
- Do not infer completion from an open pull request or a green unit test alone. Reconcile Jira status with pull request state, required checks, relevant end-to-end validation, deployment evidence, and operational verification.
