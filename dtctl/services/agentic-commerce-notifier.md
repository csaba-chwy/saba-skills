# `agentic-commerce-notifier`

- Preserve the target's exact environment and region tags in service and workload filters.
- If logs lack `dt.entity.service` or `service.name`, retrieve them by the exact tagged workload and inspect correlation fields before choosing a pivot.
- Query spans by the entity ID resolved for the selected context. Queue-processing spans can expose `start_time`, `trace.id`, `span.id`, workload, and pod fields.
- If notifier-local logs lack native trace and span IDs, map one selected span to logs using its exact pod and smallest useful time window. Label this as supporting evidence, not an exact ID join.
- Re-probe enrichment in each target environment; do not assume behavior observed in one environment applies to another.
