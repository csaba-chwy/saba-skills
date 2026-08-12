# `chewy-portal`

Observed in production and staging `use1` telemetry on 2026-08-12; re-probe current enrichment before relying on it.

- Exact tagged `chewy-portal` discovery can return multiple active entity IDs for the same workload. Main pods use a `chewy-portal-...` prefix; bot-traffic pods use `chewy-portal-bot-traffic-...`. Rank IDs by request count and inspect a small span sample to select the intended traffic class; query both when the question covers all portal traffic.
- Request-count metrics expose `failed`, `endpoint.name`, HTTP method/status, workload, and version dimensions separately for each entity.
- Sampled warning/error logs carried `dt.entity.service`, 32-character `trace_id`, and 16-character `span_id`, while `service.name` and dotted log ID fields were absent.
- A narrow trace pivot verified that the log IDs matched span `trace.id` and `span.id`, including cross-service spans. Reuse native ID correlation after re-probing current records.
- Spans include root server, client, and internal Node.js work with pod/workload identity. Sampled spans lacked captured X-Request-ID, so prefer native trace/span IDs.
