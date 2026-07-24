# AGC and AGC-98 example

Use this reference for the Agentic Commerce board and the `agentic-commerce-orchestrator` repository.

## Board pattern

- Project key: `AGC`; project name: Agentic Commerce.
- Tie Stories and applicable Bugs to an Epic.
- Use Jira `Blocks`, `Relates`, and `Duplicate` links for delivery relationships.
- Keep descriptions focused on the current desired outcome, testable failure paths, scope boundaries, and validation.
- Use readable link labels and summarize the facts needed to perform the work.

Internal guidance:

- [Ticket Writing and JIRA Overview](https://chewyinc.atlassian.net/wiki/spaces/cert/pages/1611694890/Ticket+Writing+and+JIRA+Overview)
- [Code Factory ticket-writing guidance](https://chewyinc.atlassian.net/wiki/spaces/SDD/pages/5113970752/Code+Factory+Ticket-Writing+Do+s+and+Don+t+s)

## AGC-98 pattern

[AGC-98 — UCP Cart Session Support](https://chewyinc.atlassian.net/browse/AGC-98) is a useful ownership example:

- The Epic owns Cart business workflows and explicitly leaves shared v2 routing, DTO, versioning, and protocol infrastructure to [AGC-235 — UCP v2 support](https://chewyinc.atlassian.net/browse/AGC-235).
- Child Stories isolate retrieval, replacement, conversion, shared-protocol application, synchronization, and deep E2E coverage.
- Blocking work is represented with Jira links instead of a prose dependency section.
- Runtime Stories require bounded success/failure metrics, trace correlation, and PII-safe MDC logging in the same ticket.

Default new tickets to the three-section templates even when an existing Epic has extra headings. Fold ownership boundaries into the Description paragraph and Acceptance Criteria unless extra structure is essential.

## Repository evidence

Read `service_description.md` first. For observability and test scope, inspect:

- `src/main/java/com/chewy/sf/checkout/o11y/MetricsTracker.java`
- request-context, trace, MDC, and logging helpers and their callers
- `src/e2eTest` for current UCP end-to-end coverage

Follow the existing metrics flow and bounded tag conventions. Keep request, Cart, Checkout, customer, and order identifiers in traces and PII-safe MDC rather than metric tags.
