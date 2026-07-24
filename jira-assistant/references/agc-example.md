# Jira ownership and observability example

Use this reference for a commerce board and a service repository.

## Board pattern

- Project key: `SHOP`; project name: Commerce Platform.
- Tie Stories and applicable Bugs to an Epic.
- Use Jira `Blocks`, `Relates`, and `Duplicate` links for delivery relationships.
- Keep descriptions focused on the current desired outcome, testable failure paths, scope boundaries, and validation.
- Use readable link labels and summarize the facts needed to perform the work.

Reference guidance:

- Use the team's published ticket-writing guide.
- Keep organization-specific links in the local environment configuration.

## Epic ownership pattern

[SHOP-98 — Cart Session Support](https://jira.example.com/browse/SHOP-98) is a useful ownership example:

- The Epic owns cart business workflows and explicitly leaves shared protocol infrastructure to [SHOP-235 — Protocol support](https://jira.example.com/browse/SHOP-235).
- Child Stories isolate retrieval, replacement, conversion, shared-protocol application, synchronization, and deep E2E coverage.
- Blocking work is represented with Jira links instead of a prose dependency section.
- Runtime Stories require bounded success/failure metrics, trace correlation, and PII-safe MDC logging in the same ticket.

Default new tickets to the three-section templates even when an existing Epic has extra headings. Fold ownership boundaries into the Description paragraph and Acceptance Criteria unless extra structure is essential.

## Repository evidence

Read `service_description.md` first. For observability and test scope, inspect:

- `src/main/java/com/example/checkout/o11y/MetricsTracker.java`
- request-context, trace, MDC, and logging helpers and their callers
- `src/e2eTest` for current end-to-end coverage

Follow the existing metrics flow and bounded tag conventions. Keep request, Cart, Checkout, customer, and order identifiers in traces and PII-safe MDC rather than metric tags.
