# Concise Jira templates

Default to a 40–70 word Description, one useful link, and three brief acceptance criteria. Avoid repetition and optional implementation detail.

## Epic

**Summary:** `[Outcome or capability]`

```markdown
## Description

[State the outcome, reason, and ownership boundary.]

## Relevant Links

- [Primary context](https://example.com/context)

## Acceptance Criteria

- [Measurable outcome and material failure behavior.]
- [Critical boundary and relevant E2E validation.]
- [Required bounded metrics, traces, and PII-safe logs/MDC.]
```

## Story

**Summary:** `[Verb] [specific user or system outcome]`

```markdown
## Description

[State the outcome, current gap, and boundary.]

## Relevant Links

- [Primary context](https://jira.example.com/browse/SHOP-123)

## Acceptance Criteria

- [Behavior, material failure path, and compatibility boundary.]
- [Focused automated and relevant E2E tests.]
- [Bounded metrics, traces, and PII-safe logs/MDC.]
```

## Bug adaptation

Use the Story template. State conditions, actual versus expected behavior, impact, and evidence. Require the fix, relevant E2E regression coverage, and telemetry.

## Link style

Use short labels, not raw URLs.
