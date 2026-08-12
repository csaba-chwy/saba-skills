# `cart-a`

Observed in production and staging `use1` telemetry on 2026-08-12; re-probe current enrichment before relying on it.

- Use the exact tagged `cart-a` name for service discovery and the exact tagged workload for logs. Duplicate historical IDs can exist outside the active target; rank exact-name candidates by `dt.service.request.count`.
- Request-count metrics expose `failed`, `endpoint.name`, HTTP method/status, workload, and version dimensions. Use these for exact failure trends and endpoint rankings.
- Sampled workload logs lacked service-name, entity, trace, and span enrichment. Do not expect a log-to-trace pivot; use exact workload plus pod/time evidence.
- Spans expose pod/workload identity and HTTP server/client activity. Root server spans commonly carry `http.request.header.x-request-id`; treat it as sensitive and use it only when the investigation needs request-level correlation.
