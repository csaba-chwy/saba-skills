# `[stg][use1]sf-item`

- Context: `nonprod`
- Service entity ID: `SERVICE-E8F750E0328DD297`
- Filtering logs by the service entity ID is selective and reliable.
- Logs populate `trace_id` and `span_id`. The similarly named `trace.id` and `span.id` fields are null on these log records, and `service.name` is also null.
- Request lifecycle records such as `received_request` and `processed_request` can share the same trace and span IDs, so an exact `trace_id` pivot connects them without reading full log content.
- The original context credential returned `NOT_AUTHORIZED_FOR_TABLE` for `fetch spans`; span-table access succeeded after the dedicated nonproduction credential was refreshed. Probe capabilities instead of inferring them from the `platform token` auth type.
