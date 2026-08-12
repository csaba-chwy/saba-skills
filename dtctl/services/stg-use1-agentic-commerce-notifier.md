# `[stg][use1]agentic-commerce-notifier`

- Context: `nonprod`
- Service entity ID: `SERVICE-96B2F23C4556A54F`
- Do not rely on the service entity ID for logs: sampled records had null `dt.entity.service` and `service.name`.
- Use the exact workload `[stg][use1]agentic-commerce-notifier` to retrieve logs. Sampled records also had null `trace_id`, `span_id`, `trace.id`, and `span.id`, with no trace/span marker names in message text.
- The `nonprod` context can query notifier spans by the service entity ID. Sampled spans represented SQS queue processing and exposed `start_time`, `trace.id`, `span.id`, workload, and pod fields.
- An exact trace-ID pivot connected notifier spans to spans and logs from other services. Because the notifier's own logs lacked IDs, they were not natively associated with those spans in the trace view. Build a separate mapping for notifier-local logs using exact pod plus the smallest span-time window, and distinguish that supporting evidence from an exact ID join.
