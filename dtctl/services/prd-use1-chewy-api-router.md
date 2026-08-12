# `[prd][use1]chewy-api-router`

- Context: `prod`
- Service entity ID: `SERVICE-592C600D2FAD64FA`
- The `dt.service.request.count` metric exposes `failed` and `endpoint.name`; use `failed == true` for exact failure trends and rankings before raw telemetry.
- Treat `endpoint.name` values such as GraphQL query and mutation names as router operations, not confirmed downstream subgraph names.
- Use the exact workload `[prd][use1]chewy-api-router` for logs that lack `dt.entity.service`, `service.name`, `trace_id`, and `span_id` enrichment.
- High traffic can exhaust a 5 GB scan cap in an unsampled minute of spans or 15 minutes of logs. A `--default-sampling-ratio 100` workload log query completed below the cap and reported `sampled: true`; retain the requested large range and increase sampling before narrowing it.
