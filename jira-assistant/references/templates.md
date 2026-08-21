# Concise Jira templates

Default to the shortest ticket that still gives the assignee a clear outcome and definition of done. Add context, links, validation, and service-specific detail only when they change execution or acceptance. Avoid implementation inventories, proof-of-testing checklists, and generic E2E or observability statements.

## Epic

**Summary:** `[Outcome or capability]`

```markdown
## Description

[State the outcome, reason, and ownership boundary.]

## Acceptance Criteria

- [Measurable outcome.]
- [Only additional boundary or validation needed to define completion.]
```

## Task or Story

**Summary:** `[Verb] [specific user or system outcome]`

```markdown
## Description

[State the outcome and essential boundary in one or two sentences.]

## Acceptance Criteria

- [Primary observable outcome.]
- [Only other condition that materially changes whether the work is done.]
```

Add a `Relevant Links` section only when a link reduces necessary prose or identifies separately owned work. Keep the ticket understandable without copying the linked issue's requirements.

## Bug adaptation

Use the Task or Story template. State the reproduction conditions, actual versus expected behavior, and impact concisely. Add regression coverage or telemetry criteria only when they are material to accepting the fix.

## Link style

Use short labels, not raw URLs.
