# Concise Jira templates

Use the smallest structure that makes the outcome executable and verifiable. Omit optional sections, links, and criteria that add no useful information. Avoid implementation inventories, proof-of-testing checklists, and generic E2E or observability statements.

## Epic

**Summary:** `[Outcome or capability]`

```markdown
## Description

[State the outcome, reason, and ownership boundary in a short paragraph.]

## Acceptance Criteria

- [Measurable outcome or boundary.]
- [Material delivery or verification condition, if needed.]
```

## Task or Story

**Summary:** `[Verb] [specific user or system outcome]`

```markdown
## Description

[State the outcome and current gap in one or two sentences.]

## Acceptance Criteria

- [Observable behavior and important boundary.]
- [Proportionate validation, if it needs to be explicit.]
```

For very small work, one Description sentence and one acceptance criterion can be enough.

## Bug adaptation

State the reproduction conditions, actual versus expected behavior, and impact without a long narrative. Acceptance criteria should require the fix and the smallest useful regression proof. Add E2E or telemetry work only when the risk or current signal gap warrants it.

## Relationships and links

- Do not list Jira issue URLs, dependencies, blockers, duplicates, or related tickets in the body.
- Use the Jira parent field for hierarchy and first-class `Blocks`, `Duplicate`, or `Relates` issue links for relationships. Verify directional links in raw Jira output.
- Add an optional `Relevant Links` section only for non-Jira context that materially helps execution, such as a design or technical document. Use short human-readable labels rather than raw URLs.
