# `agentic-commerce-orchestrator`

- Preserve the target's exact environment and region tags in service and workload filters.
- Retrieve logs by the exact workload when service enrichment is absent, and inspect whether `trace_id` and `span_id` are populated before choosing a correlation mode.
- Start with `dt.service.request.count`, then query root spans in a selected active interval. If a workload log probe reaches the 5 GB cap, use the selected span's exact pod and time interval before pivoting by returned IDs.
- Filter HTTP root spans with `request.is_root_span == true`. Check the string-array field `http.request.header.x-request-id` instead of assuming top-level `x-request-id` or `request_attribute.x-request-id` is populated.
- Reuse native trace/span mapping only when sampled log IDs match the trace and span IDs. Re-probe this relationship in each target environment.
