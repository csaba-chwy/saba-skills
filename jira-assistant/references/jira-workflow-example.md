# Jira ownership and observability example

Use this reference for a commerce board and a service repository.

## Board pattern

- Project key: `SHOP`; project name: Commerce Platform.
- Tie Stories and applicable Bugs to an Epic.
- Use Jira `Blocks`, `Relates`, and `Duplicate` links for delivery relationships.
- Keep descriptions focused on the current desired outcome and essential scope boundary.
- Keep acceptance criteria to the few conditions that materially determine completion; do not copy discovery notes or linked-ticket checklists.
- Use readable link labels and summarize the facts needed to perform the work.

Reference guidance:

- Use the team's published ticket-writing guide.
- Keep organization-specific links in the local environment configuration.

## Epic ownership pattern

[SHOP-98 — Cart Session Support](https://jira.example.com/browse/SHOP-98) is a useful ownership example:

- The Epic owns cart business workflows and explicitly leaves shared protocol infrastructure to [SHOP-235 — Protocol support](https://jira.example.com/browse/SHOP-235).
- Child Stories isolate retrieval, replacement, conversion, shared-protocol application, synchronization, and deep E2E coverage.
- Blocking work is represented with Jira links instead of a prose dependency section.
- Runtime Stories include E2E or observability criteria only when those are material to accepting the behavior change.

Default new tickets to the two-section template even when an existing Epic has extra headings. Add links or extra structure only when they reduce ambiguity.

## Repository evidence

Read `service_description.md` first. For observability and test scope, inspect:

- `src/main/java/com/example/checkout/o11y/MetricsTracker.java`
- request-context, trace, MDC, and logging helpers and their callers
- `src/e2eTest` for current end-to-end coverage

Use this evidence to identify the minimum acceptance boundary and avoid duplicates. Do not copy every implementation or telemetry detail into the ticket. When telemetry is in scope, follow existing metrics flow and bounded tag conventions; keep request, Cart, Checkout, customer, and order identifiers in traces and PII-safe MDC rather than metric tags.
