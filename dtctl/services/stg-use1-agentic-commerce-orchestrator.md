# `[stg][use1]agentic-commerce-orchestrator`

- Context: `nonprod`
- Service entity ID: `SERVICE-E5986BAFC3F56E4C`
- Logs are retrieved reliably by exact workload and can populate `trace_id` and `span_id` even when `dt.entity.service` and `service.name` are null.
- Start with `dt.service.request.count` for both recent and historical investigations, then query root spans in the active minute. A steady baseline was distinguishable from traffic spikes. A one-minute workload log probe can still reach the 5 GB cap, so use the selected span's exact pod and time interval, then pivot by returned exact IDs; do not widen the window or raise the cap.
- Filter HTTP root spans with `request.is_root_span == true`. The captured request ID is in the string-array field `http.request.header.x-request-id`; sampled top-level `x-request-id` and `request_attribute.x-request-id` fields were null.
- Sampled logs had `trace_id` and `span_id` values matching the trace and root-span IDs. Reuse this native mapping: the orchestrator logs are already available from the corresponding trace/span, so query them by exact IDs instead of building a pod/time mapping. Logs exposed trace/span IDs but not the captured header field.
