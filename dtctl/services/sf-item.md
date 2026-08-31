# `sf-item`

Request-count metric enrichment was re-probed in production on 2026-08-31.

- Preserve the target's exact environment and region tags in service and workload filters.
- `dt.service.request.count` exposes `primary_tags.version`; observed values such as `0.180.0` identify the Service Version. Filter by the exact value and group by regional `service.name` to locate first traffic for a deployment.
- Prefer the resolved service entity ID for logs when it is selective and populated; confirm this enrichment in the target environment.
- Inspect log-side `trace_id` and `span_id`. If both are populated, pivot by exact IDs; do not substitute the similarly named `trace.id` and `span.id` fields without checking them.
- Request lifecycle records such as `received_request` and `processed_request` can share trace and span IDs, so an exact `trace_id` pivot can connect them without reading full log content.
- Probe span-table access independently. Treat `NOT_AUTHORIZED_FOR_TABLE` as a credential capability boundary rather than inferring access from the authentication type.
