# `purchase-app`

Observed in live telemetry through 2026-08-13; re-probe current enrichment before relying on it.

- Translate the logical name `purchase-app` to the telemetry stem `purchaseapp`. Use that stem in logical selectors; the hyphenated form returned no service, metric, or workload data.
- The shared logical metric selector matched the explicit regional request total on 2026-08-13.
- Request-count metrics expose `failed`, `endpoint.name`, HTTP method/status, workload, and version dimensions.
- Sampled `purchaseapp` workload logs lacked service-name, entity, trace, and span enrichment. Use exact workload plus pod/time evidence.
- Spans expose pod/workload identity and HTTP server/client activity, but sampled spans lacked captured X-Request-ID. Root server spans can still provide routes and exact trace/span IDs.
