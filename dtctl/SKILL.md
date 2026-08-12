---
name: dtctl
description: Investigate Dynatrace services with dtctl by selecting the correct nonprod or prod context, locating traffic and failures cheaply through metric dimensions, and then running safe, bounded or sampled log and trace queries. Use for error analysis over short or long time ranges, log errors, trace-to-log correlation, deployment symptoms, Kubernetes workload logs, service latency, and service-specific observability investigations.
---

# Dynatrace investigation with dtctl

Use this skill for **read-only Grail investigation**. The configured identity may be able to query logs while being denied access to spans. Probe trace access with a narrow query and treat `NOT_AUTHORIZED_FOR_TABLE` as a permission boundary; do not try to work around it or switch tools implicitly.

## Start safely

Select the context from the service's leading environment tag before any query. Use `prod` only for `[prd]`; use `nonprod` for `[stg]`, `[qat]`, and `[dev]`. If the target has no recognized tag and the environment is not otherwise explicit, stop and ask instead of guessing. Never fall back across the production boundary.

```bash
case "$SERVICE_NAME" in
  "[prd]"*) DT_CONTEXT=prod ;;
  "[stg]"*|"[qat]"*|"[dev]"*) DT_CONTEXT=nonprod ;;
  *) print -u2 'Cannot determine Dynatrace context from service name'; exit 1 ;;
esac
dtctl config describe-context "$DT_CONTEXT" --plain
dtctl --context "$DT_CONTEXT" auth status --plain
```

Pass `--context "$DT_CONTEXT"` on every subsequent `dtctl` query or verification; do not rely on the current default context. Require preconfigured read-only `nonprod` and `prod` contexts. If either context is unavailable or the user asks to refresh credentials, direct them to [README.md](README.md) instead of embedding workstation setup in the investigation workflow. Do not use `dtctl auth whoami`; it requires an OAuth/JWT identity scope that a platform token may not have.

Resolve an exact service name to its entity ID before querying telemetry. If more than one record matches, disambiguate before continuing.

```bash
dtctl --context "$DT_CONTEXT" verify query 'fetch dt.entity.service | filter entity.name == "SERVICE-NAME" | fields id, entity.name | limit 20' --plain
dtctl --context "$DT_CONTEXT" query 'fetch dt.entity.service | filter entity.name == "SERVICE-NAME" | fields id, entity.name | limit 20' --default-scan-limit-gbytes 5 -o json --plain
```

## Find traffic and failures cheaply first

Use `dt.service.request.count` before fetching logs or spans for a resolved service. Metrics are substantially cheaper for locating traffic and failure hotspots; raw telemetry is for classifying errors and retrieving representative evidence.

Do not assume that failures use a separate metric key. Inspect the metric catalog for the exact service first. In span-derived service metrics, `dt.service.request.count` can expose a boolean `failed` dimension plus dimensions such as `endpoint.name`. Treat dimensions as tenant- and service-specific: use only fields returned by the catalog query.

Skip the metric step only when the user already supplied an exact trace/request ID with a narrow window, or when the target has no service entity or request-count metric. In the latter case, use the exact workload and apply the raw-data sampling workflow below for a large requested range.

```bash
# Recent activity at one-minute resolution.
dtctl --context "$DT_CONTEXT" query 'timeseries requests=sum(dt.service.request.count), interval:1m, by:{dt.entity.service}, filter:{dt.entity.service == "SERVICE-xxx"}, from:-15m | fields timeframe, interval, dt.entity.service, requests | limit 20' -o json --plain

# A historical window at coarse resolution.
dtctl --context "$DT_CONTEXT" query 'timeseries requests=sum(dt.service.request.count), interval:15m, by:{dt.entity.service}, filter:{dt.entity.service == "SERVICE-xxx"}, from:-24h | fields timeframe, interval, dt.entity.service, requests | limit 20' -o json --plain

# Discover whether request count exposes failure and ranking dimensions.
dtctl --context "$DT_CONTEXT" query 'metrics | filter metric.key == "dt.service.request.count" | filter dt.entity.service == "SERVICE-xxx" | fields metric.key, failed, endpoint.name, dt.entity.service, service.name, dt.metrics.source | dedup failed, endpoint.name | sort failed desc, endpoint.name asc | limit 100' -o json --plain

# Find failure hotspots across a large requested range without scanning raw spans or logs.
dtctl --context "$DT_CONTEXT" query 'timeseries failures=sum(dt.service.request.count), interval:1h, filter:{dt.entity.service == "SERVICE-xxx" and failed == true}, from:-7d | fields timeframe, interval, failures | limit 20' -o json --plain

# Rank metric dimensions across the requested range. Replace endpoint.name only with a
# dimension confirmed by the metric-catalog query.
dtctl --context "$DT_CONTEXT" query 'timeseries failures=sum(dt.service.request.count), interval:1h, by:{endpoint.name}, filter:{dt.entity.service == "SERVICE-xxx" and failed == true}, from:-7d | fieldsAdd failures_total=arraySum(failures) | fields endpoint.name, failures_total | sort failures_total desc | limit 20' -o json --plain
```

Use the metric in this order:

1. Match its timeframe to the user's requested investigation window.
2. Inspect `metrics` for the exact service to discover `failed` and available grouping dimensions.
3. For error investigations, chart `failed == true` at a resolution appropriate to the range: one minute for short incidents, 15 minutes for day-scale windows, and one hour or coarser for week-scale windows.
4. Rank confirmed dimensions such as `endpoint.name` by total failures. Use request volume as a denominator when the question concerns failure rate rather than failure count.
5. For one incident, refine a peak interval to one-minute resolution and drill into it. For analysis over a large time range, retain the requested range and use the sampling workflow below before selecting narrower examples.

The `failed` metric dimension represents failed service requests derived from spans; it is not a count of `ERROR` log records. Likewise, `endpoint.name` can describe an inbound operation rather than a downstream service or GraphQL subgraph. Do not relabel an endpoint as a subgraph unless telemetry establishes that mapping. Use metrics for exact counts, rates, rankings, and time selection; use sampled spans or logs to identify error types and supporting examples.

If the metric has no data, do not conclude that no logs exist. A service entity can exist while logs lack `dt.entity.service`; retry with the exact Kubernetes workload. Keep a short incident window bounded, or sample across the full range for a large-range analysis.

## Required query controls

Every `fetch logs` or `fetch spans` query must:

1. Use either a small metric-selected incident window or an explicit sampling ratio over a large user-requested analysis window.
2. Filter on a selective target such as an exact `dt.entity.service`, `trace_id`, `trace.id`, `k8s.namespace.name`, `k8s.workload.name`, or `host.name` before sorting or aggregation.
3. Return only fields needed for the next step and end with `limit 20` (never over 100 without a reason).
4. Use `--default-scan-limit-gbytes 5` and `-o json --plain` when executing.

A result limit does not limit Grail scan cost. A request-count metric can locate failures across a broad window without scanning raw telemetry. Before an **unsampled** raw `fetch logs` or `fetch spans` window over two hours, a weakly filtered fetch, a custom bucket, or a scan cap over 20 GB, explain the cost and get the user's approval first. Do not raise the scan cap without approval.

## Sample raw errors over large ranges

When the user asks to analyze or rank errors over a large time range, do not answer from only the latest or busiest minute. Keep the requested timeframe and introduce sampling after the metric pass:

1. Run the raw query over the full requested range with `--default-sampling-ratio 10`; use powers of ten and increase to `100`, `1000`, or higher if the 5 GB scan cap is reached.
2. Include `--metadata=scannedBytes,sampled,analysisTimeframe` and confirm `sampled` is `true` and `analysisTimeframe` matches the requested range.
3. Use the full-range sample to discover error schemas, recurring types, and candidate subgraph or dependency fields.
4. Stratify follow-up evidence using the metric timeline: sample at least a peak-failure interval and a normal-baseline interval; for multi-day ranges also cover early and late portions or relevant deployment boundaries.
5. Use exact metrics for totals and rates. Label counts or rankings computed from sampled raw records as approximate, state the sampling ratio, and do not extrapolate rare-error counts unless the sampling design supports it.
6. After classifying error types, use selective exact fields such as endpoint, subgraph, error type, trace ID, or pod to retrieve small unsampled examples when needed.

Sampling reduces scan cost while preserving coverage of the requested period. If a sampled query still reaches the cap, increase the sampling ratio before narrowing the timeframe. Narrow the timeframe only for incident drilldown, exact examples, or when sampling cannot answer the question.

```bash
# Sample error logs across a large requested range. Use the exact service entity when
# log enrichment is reliable; otherwise use the exact workload.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-7d | filter k8s.workload.name == "EXACT-WORKLOAD" | filter loglevel == "ERROR" | fields timestamp, content, trace_id, span_id, k8s.pod.name | sort timestamp desc | limit 20' --default-sampling-ratio 100 --default-scan-limit-gbytes 5 --metadata=scannedBytes,sampled,analysisTimeframe -o json --plain

# Approximate a top list only after discovering structured fields in the sample.
# Replace the placeholders with fields actually present in the sampled telemetry.
dtctl --context "$DT_CONTEXT" query 'fetch spans, from:now()-7d | filter dt.entity.service == "SERVICE-xxx" | filter span.status_code == "ERROR" | summarize sampled_errors=count(), by:{`DISCOVERED-SUBGRAPH-FIELD`, `DISCOVERED-ERROR-TYPE-FIELD`} | sort sampled_errors desc | limit 20' --default-sampling-ratio 100 --default-scan-limit-gbytes 5 --metadata=scannedBytes,sampled,analysisTimeframe -o json --plain
```

Sampling can miss rare events and can distort rankings when records have unequal inclusion behavior. Present sampled raw results as classification evidence, not exact population counts. If the metric catalog already exposes the desired grouping dimension, prefer its exact metric ranking over a sampled raw aggregation.

Validate unfamiliar DQL before executing it:

```bash
dtctl --context "$DT_CONTEXT" verify query 'fetch logs, from:now()-15m | filter dt.entity.service == "SERVICE-xxx" | limit 20' --plain
```

Read the full verifier output. Treat `SEVERE` or `QUERY_ALWAYS_EMPTY_FILTER` diagnostics as validation failures even if the command also prints `Query is valid` and exits successfully.

## Correlate logs and traces

Start from the resolved service entity and inspect the structured correlation fields in the metric-selected window. If no logs appear, retry with the exact workload. Do not assume log and span field names are identical or populated.

After selecting a representative span, determine the mapping mode before doing a separate log search:

1. Sample logs from that span's exact pod and smallest useful time window, without `content`, and inspect `trace_id` and `span_id`.
2. If both IDs are populated and match `trace.id` and `span.id` from the selected trace, reuse that native span-level mapping. These logs are already associated with the span in Dynatrace; pivot by exact `trace_id` and, when the question concerns one span, exact `span_id`. Do not replace an exact mapping with pod/time proximity.
3. If only `trace_id` matches, reuse it as a native trace-level mapping, but do not claim that a log belongs to a particular span.
4. If neither ID is available, create a separate bounded mapping: select a span, copy its exact pod, and fetch logs only around that span's execution interval. Label this as pod/time supporting evidence, not an exact trace association. If multiple spans overlap on the same pod, report the ambiguity instead of assigning a log to one of them.

Reuse a confirmed native mapping for the rest of the investigation. Re-probe after a deployment, when records have mixed enrichment, or when moving to another service; correlation is a property of the sampled telemetry, not a permanent service guarantee.

```bash
# Find log-side correlation IDs in the metric-selected window.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:"WINDOW-START", to:"WINDOW-END" | filter dt.entity.service == "SERVICE-xxx" | fields timestamp, loglevel, trace_id, span_id, k8s.workload.name, k8s.pod.name | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Retry by exact workload when logs lack service-entity enrichment.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:"WINDOW-START", to:"WINDOW-END" | filter k8s.workload.name == "EXACT-WORKLOAD" | fields timestamp, loglevel, trace_id, span_id, dt.entity.service, service.name, k8s.pod.name | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Probe native mapping more selectively after choosing one representative span.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:"SPAN-START-MINUS-SKEW", to:"SPAN-END-PLUS-SKEW" | filter k8s.pod.name == "SPAN-POD" | fields timestamp, trace_id, span_id, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Pivot from one exact log trace ID to its spans.
dtctl --context "$DT_CONTEXT" verify query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter trace.id == toUid("TRACE-ID") | fields start_time, trace.id, span.id, parent_span.id, span.name, duration, span.status_code, dt.entity.service | sort start_time asc | limit 20' --plain
dtctl --context "$DT_CONTEXT" query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter trace.id == toUid("TRACE-ID") | fields start_time, trace.id, span.id, parent_span.id, span.name, duration, span.status_code, dt.entity.service | sort start_time asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Find all logs carrying that exact trace ID, including other services when present.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:"WINDOW-START", to:"WINDOW-END" | filter trace_id == "TRACE-ID" | fields timestamp, loglevel, trace_id, span_id, dt.entity.service, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# When native IDs are absent, map one selected span to logs by exact pod and a tight
# interval computed locally from span start_time, duration, and a small clock-skew margin.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:"SPAN-START-MINUS-SKEW", to:"SPAN-END-PLUS-SKEW" | filter k8s.pod.name == "SPAN-POD" | fields timestamp, loglevel, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Find HTTP root spans with a captured X-Request-ID header in one narrow window.
dtctl --context "$DT_CONTEXT" query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter dt.entity.service == "SERVICE-xxx" | filter request.is_root_span == true | filter isNotNull(`http.request.header.x-request-id`) | fields start_time, trace.id, span.id, span.name, span.kind, `http.request.header.x-request-id`, http.request.method, http.route, k8s.pod.name | sort start_time desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain
```

Log `trace_id` is a string, while span `trace.id` is a UID; use `toUid("TRACE-ID")` for the span-side comparison. Spans use `start_time`, while logs use `timestamp`. Correlate records locally by exact trace ID and then exact span ID. Use time only to order exact matches or as the explicitly labeled fallback when native IDs are absent. Do not force a server-side join unless separate bounded pivots are insufficient, because a join can substantially increase scan cost. Include `content` only when the message text is necessary; it can contain customer or request data.

Captured HTTP headers use the `http.request.header.<lowercase-name>` namespace and can be arrays. For X-Request-ID, query the backticked field `http.request.header.x-request-id`; do not assume top-level `x-request-id` or `request_attribute.x-request-id` is populated. Treat captured header values as sensitive and omit their values from summaries unless the user explicitly needs them.

If the span query returns `NOT_AUTHORIZED_FOR_TABLE`, report that trace data could not be inspected with the current identity. Continue with the log-side `trace_id` pivot when it still answers part of the question, and state clearly that this is correlation evidence from logs rather than verified span data.

If both structured correlation fields and message-level trace/span markers are absent, continue the log investigation using exact workload, pod, and timestamp filters. Report that log-to-trace correlation is unavailable for the sampled records; do not infer that the service emits no traces.

### Verified service behavior

For `[stg][use1]sf-item` in nonproduction:

- Resolve the service name to `SERVICE-E8F750E0328DD297`; filtering logs by this entity ID is selective and reliable.
- The logs populate `trace_id` and `span_id`. The similarly named `trace.id` and `span.id` fields are null on these log records, and `service.name` is also null.
- Request lifecycle records such as `received_request` and `processed_request` can share the same trace and span IDs, so an exact `trace_id` pivot connects them without reading full log content.
- The original context credential returned `NOT_AUTHORIZED_FOR_TABLE` for `fetch spans`; span-table access succeeded after the dedicated nonproduction credential was refreshed. Probe capabilities instead of inferring them from the `platform token` auth type.

For `[stg][use1]agentic-commerce-notifier` in nonproduction:

- Resolve the service name to `SERVICE-96B2F23C4556A54F`, but do not rely on that ID for its logs: sampled records had null `dt.entity.service` and `service.name`.
- Use the exact workload `[stg][use1]agentic-commerce-notifier` to retrieve logs. Sampled records also had null `trace_id`, `span_id`, `trace.id`, and `span.id`, with no trace/span marker names in message text.
- The `nonprod` context can query notifier spans by `SERVICE-96B2F23C4556A54F`. Sampled spans represented SQS queue processing and exposed `start_time`, `trace.id`, `span.id`, workload, and pod fields.
- An exact trace-ID pivot connected notifier spans to spans and logs from other services. Because the notifier's own logs lacked IDs, they were not natively associated with those spans in the trace view. Build a separate mapping for notifier-local logs using exact pod plus the smallest span-time window, and distinguish that supporting evidence from an exact ID join.

For `[stg][use1]agentic-commerce-orchestrator` in nonproduction:

- Resolve the service name to `SERVICE-E5986BAFC3F56E4C`. Its logs are retrieved reliably by exact workload and can populate `trace_id` and `span_id` even when `dt.entity.service` and `service.name` are null.
- Start with `dt.service.request.count` for both recent and historical investigations, then query root spans in the active minute. A steady baseline was distinguishable from traffic spikes. A one-minute workload log probe can still reach the 5 GB cap, so use the selected span's exact pod and time interval, then pivot by returned exact IDs; do not widen the window or raise the cap.
- Filter HTTP root spans with `request.is_root_span == true`. The captured request ID is in the string-array field `http.request.header.x-request-id`; sampled top-level `x-request-id` and `request_attribute.x-request-id` fields were null.
- Sampled logs had `trace_id` and `span_id` values matching the trace and root-span IDs. Reuse this native mapping: the orchestrator logs are already available from the corresponding trace/span, so query them by exact IDs instead of building a pod/time mapping. Logs exposed trace/span IDs but not the captured header field.

For `[prd][use1]chewy-api-router` in production:

- Resolve the service name to `SERVICE-592C600D2FAD64FA`. Its `dt.service.request.count` metric exposes `failed` and `endpoint.name`; use `failed == true` for exact failure trends and rankings before raw telemetry.
- Treat `endpoint.name` values such as GraphQL query and mutation names as router operations, not confirmed downstream subgraph names.
- Use the exact workload `[prd][use1]chewy-api-router` for logs that lack `dt.entity.service`, `service.name`, `trace_id`, and `span_id` enrichment.
- High traffic can exhaust a 5 GB scan cap in an unsampled minute of spans or 15 minutes of logs. A `--default-sampling-ratio 100` workload log query completed below the cap and reported `sampled: true`; retain the requested large range and increase sampling before narrowing it.

## Other useful patterns

```bash
# Recent errors for one service
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-15m | filter dt.entity.service == "SERVICE-xxx" | filter loglevel == "ERROR" | fields timestamp, content, trace_id, span_id, k8s.pod.name | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# A Kubernetes workload during a specific incident window
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-30m | filter k8s.namespace.name == "namespace" | filter k8s.workload.name == "workload" | fields timestamp, loglevel, content, trace_id, span_id, k8s.pod.name | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Failed-request trend for a known service; prefer this metric over scanning logs.
dtctl --context "$DT_CONTEXT" query 'timeseries failures=sum(dt.service.request.count), interval:5m, filter:{dt.entity.service == "SERVICE-xxx" and failed == true}, from:-1h | fields timeframe, interval, failures | limit 20' -o json --plain
```

Use a known entity ID or exact workload/namespace; do not begin with a tenant-wide text search. Treat telemetry as potentially sensitive and include only necessary fields in commands and summaries.

## Out of scope

Do not create, edit, apply, delete, share, or restore dashboards, notebooks, workflows, settings, extensions, buckets, or other Dynatrace resources. If a request needs one of those operations, state that this skill supports read-only telemetry investigation only.
