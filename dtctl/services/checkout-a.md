# `checkout-a`

Observed in production and staging `use1` telemetry on 2026-08-12; re-probe current enrichment before relying on it.

- Use the exact tagged `checkout-a` name and workload. Exact-name discovery can return low-traffic duplicate IDs; prefer the entity carrying current request volume.
- Request-count metrics expose `failed`, `endpoint.name`, HTTP method/status, workload, and version dimensions.
- Workload logs have mixed enrichment. Some records carry `dt.entity.service` and `trace_id` but no `span_id`; other records carry none of them, and `service.name` is absent.
- Observed log `trace_id` values were 5–15 characters, not 32-character trace UIDs. Treat them as application-local correlation keys; do not pass them to `toUid` or claim native trace correlation.
- Spans expose pod/workload identity, HTTP server/client activity, routes on root spans, and commonly captured X-Request-ID values. Use pod/time fallback for log evidence unless a newly sampled record proves native IDs.
