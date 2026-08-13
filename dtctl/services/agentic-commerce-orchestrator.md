# `agentic-commerce-orchestrator`

- Select logs across regions with `log.source == "agentic-commerce-orchestrator"` plus the requested `env`. A staging probe on 2026-08-13 returned only the expected `use1` and `use2` workloads; keep the workload in the first grouped result and fall back to exact workloads if that changes.
- `dt.entity.service.name` and `service.name` were null on the validated orchestrator logs. Inspect whether `trace_id` and `span_id` are populated before choosing a correlation mode.
- Start with `dt.service.request.count`, then query root spans in a selected active interval. If a workload log probe reaches the 5 GB cap, use the selected span's exact pod and time interval before pivoting by returned IDs.
- Filter HTTP root spans with `request.is_root_span == true`. Check the string-array field `http.request.header.x-request-id` instead of assuming top-level `x-request-id` or `request_attribute.x-request-id` is populated.
- Reuse native trace/span mapping only when sampled log IDs match the trace and span IDs. Re-probe this relationship in each target environment.

## Agentic session metrics

- Use the OpenTelemetry counters `agentic.commerce.orch.sessions.created.count`, `agentic.commerce.orch.sessions.retrieved.count`, `agentic.commerce.orch.sessions.updated.count`, `agentic.commerce.orch.sessions.canceled.count`, and `agentic.commerce.orch.sessions.completed.count`. The cancellation key uses `canceled` with one `l`.
- Query a known lifecycle key over the requested timeframe even when a short `metrics` catalog query omits it; infrequent lifecycle metrics may have no recent catalog record. Treat an empty series as no points in that context and timeframe, not proof that the instrumentation does not exist.
- Group lifecycle counters by the useful custom dimensions `chewy.api.agentic.protocol.name`, `chewy.api.agentic.protocol.version`, `chewy.api.endpoint`, `chewy.client.id`, `chewy.item.count`, `chewy.success`, `chewy.traffic.test`, and `traffic.internal.test`.
- Select all regional lifecycle series with the requested environment prefix and the `]agentic-commerce-orchestrator` suffix on `service.name`. Group by `service.name` only when a regional cross-check is needed; omit it to aggregate regions in one query. A production comparison on 2026-08-13 matched the explicit `use1` plus `use2` created-session total exactly.
- Interpret the observed endpoints as lifecycle operations: `/api/ucp/v1/checkout-sessions` for creation, `/api/ucp/v1/checkout-sessions/{id}` for retrieval or update, `/api/ucp/v1/checkout-sessions/{id}/cancel` for cancellation, and `/api/ucp/v1/checkout-sessions/{id}/complete` for completion.
- Use `chewy.success` for lifecycle outcome, `chewy.client.id` for partner/client attribution, `chewy.item.count` for affected cart size, and the two test-traffic fields to separate synthetic or internal traffic. Group before filtering because Boolean-like tag values and null sentinels can differ across contexts or instrumentation versions.
- Use `agentic.commerce.orch.message.error.count` with `chewy.message.error.code` to classify validation failures, and `agentic.commerce.orch.request.count` for overall agentic API request volume; do not substitute either for the lifecycle counters.

```bash
dtctl --context "$DT_CONTEXT" query 'timeseries sessions=sum(agentic.commerce.orch.sessions.created.count), interval:15m, by:{chewy.client.id, chewy.success}, filter:{startsWith(service.name, "[prd]") and endsWith(service.name, "]agentic-commerce-orchestrator") and chewy.traffic.test == "false" and traffic.internal.test == "false"}, from:-24h | fieldsAdd sessions_total=arraySum(sessions) | fields chewy.client.id, chewy.success, sessions_total | sort sessions_total desc | limit 20' -o json --plain
```
