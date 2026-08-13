# `cart-b`

Observed in live telemetry on 2026-08-12; re-probe current enrichment before relying on it.

- Use the exact tagged `cart-b` name and workload. Rank any duplicate exact-name entities by request traffic before selecting one.
- Request-count metrics expose `failed`, `endpoint.name`, HTTP method/status, workload, and version dimensions. Some metric rows represent non-HTTP or partially enriched operations, so group only by dimensions present in the catalog result.
- Sampled workload logs lacked service-name, entity, trace, and span enrichment. Correlate a selected span to logs only by exact pod and a tight time window, labeled as supporting evidence.
- Spans include root server, client, and internal work. X-Request-ID is common on HTTP root spans but absent on some operations; probe rather than requiring it.
