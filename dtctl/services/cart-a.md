# `cart-a`

Observed in live telemetry through 2026-08-13; re-probe current enrichment before relying on it.

- The shared logical metric selector matched the explicit regional request total. Duplicate historical IDs can still exist when a span investigation needs entity resolution.
- Request-count metrics expose `failed`, `endpoint.name`, HTTP method/status, workload, and version dimensions. Use these for exact failure trends and endpoint rankings.
- Sampled workload logs lacked service-name, entity, trace, and span enrichment. Do not expect a log-to-trace pivot; use exact workload plus pod/time evidence.
- Spans expose pod/workload identity and HTTP server/client activity. Root server spans commonly carry `http.request.header.x-request-id`; treat it as sensitive and use it only when the investigation needs request-level correlation.
