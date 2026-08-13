# `cart-a`

Observed in production and staging telemetry through 2026-08-13; re-probe current enrichment before relying on it.

- The staging logical log selector `log.source == "cart-a" and env == "stg"` returned only the expected `use1` and `use2` workloads. Use it across regions, retaining workload in the first grouped result.
- The staging metric selector based on the `[stg]` prefix and `]cart-a` suffix matched the explicit `use1` plus `use2` request total exactly. Duplicate historical IDs can still exist when a span investigation needs entity resolution.
- Request-count metrics expose `failed`, `endpoint.name`, HTTP method/status, workload, and version dimensions. Use these for exact failure trends and endpoint rankings.
- Sampled workload logs lacked service-name, entity, trace, and span enrichment. Do not expect a log-to-trace pivot; use exact workload plus pod/time evidence.
- Spans expose pod/workload identity and HTTP server/client activity. Root server spans commonly carry `http.request.header.x-request-id`; treat it as sensitive and use it only when the investigation needs request-level correlation.
