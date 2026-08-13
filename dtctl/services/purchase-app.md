# `purchase-app`

Observed in production and staging `use1` telemetry on 2026-08-12; re-probe current enrichment before relying on it.

- Translate the logical name `purchase-app` to the telemetry stem `purchaseapp`. Preserve the original tags, producing names such as `[prd][use1]purchaseapp`; the hyphenated form returned no service, metric, or workload data.
- Request-count metrics expose `failed`, `endpoint.name`, HTTP method/status, workload, and version dimensions.
- Sampled `purchaseapp` workload logs lacked service-name, entity, trace, and span enrichment. Use exact workload plus pod/time evidence.
- Spans expose pod/workload identity and HTTP server/client activity, but sampled spans lacked captured X-Request-ID. Root server spans can still provide routes and exact trace/span IDs.
