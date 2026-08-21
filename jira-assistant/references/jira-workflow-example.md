# Jira ownership and observability example

Use this reference for a commerce board and a service repository.

## Board pattern

- Project key: `SHOP`; project name: Commerce Platform.
- Tie Stories and applicable Bugs to an Epic.
- Use Jira `Blocks`, `Relates`, and `Duplicate` links for delivery relationships.
- Keep descriptions focused on the current desired outcome, material failure paths, scope boundaries, and proportionate validation.
- Keep acceptance criteria to the few conditions that materially determine completion; do not copy discovery notes or linked-ticket checklists.
- Keep Jira issue references out of descriptions. Use parent fields and first-class issue links instead.

Reference guidance:

- Use the team's published ticket-writing guide.
- Keep organization-specific links in the local environment configuration.

## Epic ownership pattern

[SHOP-98 — Cart Session Support](https://jira.example.com/browse/SHOP-98) is a useful ownership example:

- The Epic owns cart business workflows and explicitly leaves shared protocol infrastructure to [SHOP-235 — Protocol support](https://jira.example.com/browse/SHOP-235).
- Child Stories isolate retrieval, replacement, conversion, shared-protocol application, synchronization, and deep E2E coverage.
- Blocking work is represented with Jira links instead of a prose dependency section.
- Runtime Stories add or change telemetry only when current signals cannot establish the needed operational outcome.

Default to the smallest useful ticket shape even when an existing Epic has extra headings. Fold ownership boundaries into the Description or Acceptance Criteria unless extra structure is essential.

## Repository evidence

When repository evidence is necessary, read `service_description.md` first and inspect only the relevant paths. Possible observability and test evidence includes:

- `src/main/java/com/example/checkout/o11y/MetricsTracker.java`
- request-context, trace, MDC, and logging helpers and their callers
- `src/e2eTest` for current end-to-end coverage

Use this evidence to identify the minimum acceptance boundary and avoid duplicates rather than copying implementation detail into the ticket. When telemetry is in scope, follow existing metrics flow and bounded tag conventions; keep request, Cart, Checkout, customer, and order identifiers in traces and PII-safe MDC rather than metric tags.
