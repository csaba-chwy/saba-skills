# `cart-spa`

Observed in production and staging `use1` telemetry on 2026-08-12; re-probe current enrichment before relying on it.

- Use the exact tagged `cart-spa` name and workload. Nonproduction exact-name discovery can return several entities; rank them by current request count and keep more than one only if the investigation covers distinct active traffic.
- Request-count metrics expose `failed`, `endpoint.name`, HTTP method/status, workload, and version dimensions.
- Sampled workload logs lacked service-name, entity, trace, and span enrichment. Use exact workload plus pod/time evidence for logs.
- Spans include server, client, and internal activity, but sampled spans lacked captured X-Request-ID. Use native span fields for trace analysis and do not assume request-header correlation is available.
