# `checkout-b`

Observed in live telemetry on 2026-08-12; re-probe current enrichment before relying on it.

- Use the exact tagged `checkout-b` name and workload. Prefer the exact-name entity with current request traffic over stale low-volume duplicates.
- Request-count metrics expose `failed`, `endpoint.name`, HTTP method/status, workload, and version dimensions; some operations omit HTTP dimensions.
- Log enrichment varies by environment and record type. Sampled records ranged from no service or correlation fields to records with `dt.entity.service` and short `trace_id` values but no `span_id`.
- Observed enriched `trace_id` values were 5–10 characters, so treat them as application-local keys rather than trace UIDs. Use exact workload and pod/time evidence unless current records prove a native 32-hex trace ID.
- Spans expose HTTP root/client activity, routes, pod/workload identity, and commonly captured X-Request-ID values.
