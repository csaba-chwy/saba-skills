# `chewy-api-router`

- Preserve the target's exact environment and region tags in service and workload filters.
- Inspect `dt.service.request.count` dimensions for the resolved entity. When available, use `failed == true` for exact failure trends and rankings before raw telemetry.
- Treat `endpoint.name` values such as GraphQL query and mutation names as router operations, not confirmed downstream subgraph names.
- Use the exact tagged workload for logs when service and correlation enrichment is absent.
- Expect high traffic to exhaust the 5 GB cap quickly. Sample across the requested range and increase the sampling ratio before narrowing the timeframe or considering a higher scan cap.
