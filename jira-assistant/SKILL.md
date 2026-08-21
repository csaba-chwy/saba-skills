---
name: jira-assistant
description: "Read, search, summarize, create, update, and groom Jira work with concise ticket content, appropriate repository evidence, explicit approval for writes, and first-class Jira relationships."
---

# Jira Assistant

## Apply senior judgment

- Lead with the outcome, ownership boundary, delivery order, and material risk.
- Treat a ticket as a concise outcome contract, not an implementation plan, research report, or proof-of-testing log.
- Keep one independently understandable outcome per Story or Bug; split unrelated or separately deployable work.
- Prefer observable behavior over implementation instructions. Make acceptance criteria brief and testable.
- Surface only decisions that materially change behavior, priority, scope, or ownership, with a recommendation and impact.

## 1. Match discovery to the request

- Treat view, audit, explain, draft, and status requests as read-only.
- Treat a request to create, update, transition, assign, comment on, or link Jira work as authorization to propose the write, not execute it. Do not write until the user approves the exact plan.
- Start with the named issues and facts needed for the request. For a simple Jira copy, field, status, or relationship task, skip repository inspection unless it would change the answer.
- When repository evidence is material, locate the root and follow its `AGENTS.md`; read `service_description.md` when present, then inspect only the relevant implementation, tests, configuration, branch state, or recent history. Do not scan the entire repository by default, and stop when the evidence is sufficient.
- For a suspected Bug, distinguish verified behavior from a hypothesis and capture only the reproduction conditions, actual and expected behavior, impact, evidence, and likely regression coverage.

## 2. Inspect Jira precisely

- Prefer the configured `jira` CLI for exact reads and all writes. Use Atlassian search for broad discovery only when needed; do not use a browser when a CLI or connector can perform the action.
- Use targeted JQL and exact reads for relevant parents, children, links, duplicates, comments, and neighboring work. Fetch independent details concurrently when useful, but keep dependent lookups sequential.
- Search for overlap before creating an issue. Use a parent for hierarchy and Jira issue links for delivery relationships: `Blocks` for directional prerequisites, `Duplicate` for duplicates, and `Relates` for a meaningful non-directional association. Confirm the direction of `blocks` / `is blocked by` in raw readback.
- Do not put Jira issue references or dependency lists in the Description or `Relevant Links`; create or update the first-class parent or issue link instead.
- For commerce-board or service-repository conventions, read [Jira workflow example](references/jira-workflow-example.md) only when relevant.

## 3. Draft the smallest useful ticket

- Use [concise templates](references/templates.md), scaled to the work rather than a word target or fixed section count.
- For small or well-understood work, prefer a one-sentence Description and one to three focused acceptance criteria. Add context only when it clarifies the contract, boundary, material failure path, rollout, or verification.
- Let research improve judgment without copying every finding, operational property, test level, or linked-ticket requirement into the ticket. For sibling tickets, repeat only the shared boundary and add service-specific criteria only for unique gaps.
- Prefer one broad maintenance or validation criterion over an inventory of possible defects and checks; name individual cases only when each changes acceptance.
- Do not repeat acceptance criteria, links, implementation detail, history, or status narration in the Description. Omit empty sections and boilerplate such as `Dependencies`, `Removed from this Story`, dated reconciliation, or “impact reviewed” statements.
- Keep non-Jira links only when they materially help execution, using short labels. Summarize the fact they support so the link is not the sole explanation.
- Include only validation proportionate to the risk. Add E2E coverage when a material runtime outcome or lifecycle path cannot be established at a lower level; otherwise name the focused test or human check that is sufficient.
- Add or change observability only when existing signals are insufficient for the runtime behavior. Prefer bounded metrics, traces, and structured PII-safe logs; keep high-cardinality identifiers out of metric tags. Do not add a generic observability criterion to every ticket.

## 4. Approve and execute writes

- Present a compact `Jira write plan` with each target, exact field or link actions, and a short content preview only for text being changed. For a simple single-issue write, this can be one concise bullet. Mention unchanged fields only when that prevents ambiguity.
- Ask the user to approve the plan. If the user changes it or execution reveals a material scope change, revise the plan and obtain approval again.
- Before executing an approved write, read and follow the [Jira CLI runbook](references/jira-cli.md). Preserve existing description content that still matters because description edits replace the full body.
- Never parallelize Jira writes or their verification. Use the smallest approved write as a canary before continuing a batch.

## 5. Verify and report concisely

- Read back every changed or created issue. Verify all changed fields plus identity and required fields; use raw output when parent, issue-link direction, comments, or metadata need confirmation.
- Report the outcome, material exceptions, and readable Jira links. Do not restate the full plan, unchanged fields, or complete ticket bodies unless the user asks.

## 6. Hand off to code, GitHub, and CI

- Treat the approved Jira outcome and acceptance criteria as the implementation contract. If implementation reveals a material mismatch, propose a Jira update instead of silently changing scope.
- Put the full Jira URL and a concise code/test mapping in Jira-backed pull requests. Link the PR back to Jira only within the approved write scope, preferring a remote link and otherwise one concise comment.
- Use GitHub checks as the CI index. For Jenkins failures, collect the run URL, failing stage, decisive error, and verification result before recommending changes. Do not infer completion from code presence, an open PR, or a green unit test alone.
