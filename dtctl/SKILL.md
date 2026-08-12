---
name: dtctl
description: Investigate Dynatrace services with dtctl by locating traffic cheaply through request-count metrics before running safe, bounded log and trace queries. Use for log errors, trace-to-log correlation, deployment symptoms, Kubernetes workload logs, service latency, and service-specific observability investigations.
---

# Dynatrace investigation with dtctl

Use this skill for **read-only Grail investigation**. The configured identity may be able to query logs while being denied access to spans. Probe trace access with a narrow query and treat `NOT_AUTHORIZED_FOR_TABLE` as a permission boundary; do not try to work around it or switch tools implicitly.

## Start safely

```bash
dtctl auth status --plain
dtctl config current-context
```

Do not use `dtctl auth whoami`; it requires an OAuth/JWT identity scope that a platform token may not have.

When the user explicitly asks to refresh this workstation's nonproduction credential from `DT_PLATFORM_TOKEN`, reload `.zshrc`, replace the `my-token` Keychain credential, and explicitly map that token into the query process. Disable shell tracing and never print the value.

```bash
set +x
source ~/.zshrc
[[ -n "${DT_PLATFORM_TOKEN:-}" ]] || { print -u2 'DT_PLATFORM_TOKEN is not set'; exit 1; }
dtctl config set-credentials my-token --token "$DT_PLATFORM_TOKEN" --plain
export DTCTL_TOKEN="$DT_PLATFORM_TOKEN"
dtctl auth status --plain
```

Resolve an exact service name to its entity ID before querying telemetry. If more than one record matches, disambiguate before continuing.

```bash
dtctl verify query 'fetch dt.entity.service | filter entity.name == "SERVICE-NAME" | fields id, entity.name | limit 20' --plain
dtctl query 'fetch dt.entity.service | filter entity.name == "SERVICE-NAME" | fields id, entity.name | limit 20' --default-scan-limit-gbytes 5 -o json --plain
```

## Find traffic cheaply first

Use `dt.service.request.count` before fetching logs or spans for a resolved service. Metrics are substantially cheaper for locating traffic; raw telemetry is for drilling into the small active window the metric identifies.

Skip the metric step only when the user already supplied an exact trace/request ID with a narrow window, or when the target has no service entity or request-count metric. In the latter case, start with an exact workload and a 15-minute log window.

```bash
# Recent activity at one-minute resolution.
dtctl query 'timeseries requests=sum(dt.service.request.count), interval:1m, by:{dt.entity.service}, filter:{dt.entity.service == "SERVICE-xxx"}, from:-15m | fields timeframe, interval, dt.entity.service, requests | limit 20' -o json --plain

# A user-approved historical window at coarse resolution.
dtctl query 'timeseries requests=sum(dt.service.request.count), interval:15m, by:{dt.entity.service}, filter:{dt.entity.service == "SERVICE-xxx"}, from:-24h | fields timeframe, interval, dt.entity.service, requests | limit 20' -o json --plain
```

Use the metric in this order:

1. Match its timeframe to the user's requested investigation window.
2. Start with `interval:1m` for a short window or `interval:15m` for a day-scale window.
3. Identify the latest active or above-baseline interval. Health checks can create a steady nonzero baseline, so do not assume every nonzero interval is user traffic.
4. Repeat the metric at one-minute resolution around a coarse candidate.
5. Fetch raw logs or spans only for that minute or the smallest incident window that answers the question.

If the metric has no data, do not conclude that no logs exist. A service entity can exist while logs lack `dt.entity.service`; retry with the exact Kubernetes workload after keeping the raw time window narrow.

## Required query controls

Every `fetch logs` or `fetch spans` query must:

1. Use the small active time range identified by the request-count metric—start with one minute and widen only when necessary.
2. Filter on a selective target such as an exact `dt.entity.service`, `trace_id`, `trace.id`, `k8s.namespace.name`, `k8s.workload.name`, or `host.name` before sorting or aggregation.
3. Return only fields needed for the next step and end with `limit 20` (never over 100 without a reason).
4. Use `--default-scan-limit-gbytes 5` and `-o json --plain` when executing.

A result limit does not limit Grail scan cost. A request-count metric can locate traffic across a broader requested window without scanning raw telemetry. Before a raw `fetch logs` or `fetch spans` window over two hours, a weakly filtered fetch, a custom bucket, or a scan cap over 20 GB, explain the cost and get the user's approval first. If the scan limit is hit, return to the metric and narrow the raw time range or filter—do not raise the cap without approval.

Validate unfamiliar DQL before executing it:

```bash
dtctl verify query 'fetch logs, from:now()-15m | filter dt.entity.service == "SERVICE-xxx" | limit 20' --plain
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
dtctl query 'fetch logs, from:"WINDOW-START", to:"WINDOW-END" | filter dt.entity.service == "SERVICE-xxx" | fields timestamp, loglevel, trace_id, span_id, k8s.workload.name, k8s.pod.name | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Retry by exact workload when logs lack service-entity enrichment.
dtctl query 'fetch logs, from:"WINDOW-START", to:"WINDOW-END" | filter k8s.workload.name == "EXACT-WORKLOAD" | fields timestamp, loglevel, trace_id, span_id, dt.entity.service, service.name, k8s.pod.name | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Probe native mapping more selectively after choosing one representative span.
dtctl query 'fetch logs, from:"SPAN-START-MINUS-SKEW", to:"SPAN-END-PLUS-SKEW" | filter k8s.pod.name == "SPAN-POD" | fields timestamp, trace_id, span_id, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Pivot from one exact log trace ID to its spans.
dtctl verify query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter trace.id == toUid("TRACE-ID") | fields start_time, trace.id, span.id, parent_span.id, span.name, duration, span.status_code, dt.entity.service | sort start_time asc | limit 20' --plain
dtctl query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter trace.id == toUid("TRACE-ID") | fields start_time, trace.id, span.id, parent_span.id, span.name, duration, span.status_code, dt.entity.service | sort start_time asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Find all logs carrying that exact trace ID, including other services when present.
dtctl query 'fetch logs, from:"WINDOW-START", to:"WINDOW-END" | filter trace_id == "TRACE-ID" | fields timestamp, loglevel, trace_id, span_id, dt.entity.service, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# When native IDs are absent, map one selected span to logs by exact pod and a tight
# interval computed locally from span start_time, duration, and a small clock-skew margin.
dtctl query 'fetch logs, from:"SPAN-START-MINUS-SKEW", to:"SPAN-END-PLUS-SKEW" | filter k8s.pod.name == "SPAN-POD" | fields timestamp, loglevel, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Find HTTP root spans with a captured X-Request-ID header in one narrow window.
dtctl query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter dt.entity.service == "SERVICE-xxx" | filter request.is_root_span == true | filter isNotNull(`http.request.header.x-request-id`) | fields start_time, trace.id, span.id, span.name, span.kind, `http.request.header.x-request-id`, http.request.method, http.route, k8s.pod.name | sort start_time desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain
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
- The original context credential returned `NOT_AUTHORIZED_FOR_TABLE` for `fetch spans`; span-table access succeeded after `my-token` was reloaded from `DT_PLATFORM_TOKEN`. Probe capabilities instead of inferring them from the `platform token` auth type.

For `[stg][use1]agentic-commerce-notifier` in nonproduction:

- Resolve the service name to `SERVICE-96B2F23C4556A54F`, but do not rely on that ID for its logs: sampled records had null `dt.entity.service` and `service.name`.
- Use the exact workload `[stg][use1]agentic-commerce-notifier` to retrieve logs. Sampled records also had null `trace_id`, `span_id`, `trace.id`, and `span.id`, with no trace/span marker names in message text.
- The `DT_PLATFORM_TOKEN` credential can query notifier spans by `SERVICE-96B2F23C4556A54F`. Sampled spans represented SQS queue processing and exposed `start_time`, `trace.id`, `span.id`, workload, and pod fields.
- An exact trace-ID pivot connected notifier spans to spans and logs from other services. Because the notifier's own logs lacked IDs, they were not natively associated with those spans in the trace view. Build a separate mapping for notifier-local logs using exact pod plus the smallest span-time window, and distinguish that supporting evidence from an exact ID join.

For `[stg][use1]agentic-commerce-orchestrator` in nonproduction:

- Resolve the service name to `SERVICE-E5986BAFC3F56E4C`. Its logs are retrieved reliably by exact workload and can populate `trace_id` and `span_id` even when `dt.entity.service` and `service.name` are null.
- Start with `dt.service.request.count` for both recent and historical investigations, then query root spans in the active minute. A steady baseline was distinguishable from traffic spikes. A one-minute workload log probe can still reach the 5 GB cap, so use the selected span's exact pod and time interval, then pivot by returned exact IDs; do not widen the window or raise the cap.
- Filter HTTP root spans with `request.is_root_span == true`. The captured request ID is in the string-array field `http.request.header.x-request-id`; sampled top-level `x-request-id` and `request_attribute.x-request-id` fields were null.
- Sampled logs had `trace_id` and `span_id` values matching the trace and root-span IDs. Reuse this native mapping: the orchestrator logs are already available from the corresponding trace/span, so query them by exact IDs instead of building a pod/time mapping. Logs exposed trace/span IDs but not the captured header field.

## Other useful patterns

```bash
# Recent errors for one service
dtctl query 'fetch logs, from:now()-15m | filter dt.entity.service == "SERVICE-xxx" | filter loglevel == "ERROR" | fields timestamp, content, trace_id, span_id, k8s.pod.name | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# A Kubernetes workload during a specific incident window
dtctl query 'fetch logs, from:now()-30m | filter k8s.namespace.name == "namespace" | filter k8s.workload.name == "workload" | fields timestamp, loglevel, content, trace_id, span_id, k8s.pod.name | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Error count trend for a known service
dtctl query 'fetch logs, from:now()-1h | filter dt.entity.service == "SERVICE-xxx" | filter loglevel == "ERROR" | makeTimeseries errors=count(), interval:5m' --default-scan-limit-gbytes 5 -o json --plain
```

Use a known entity ID or exact workload/namespace; do not begin with a tenant-wide text search. Treat telemetry as potentially sensitive and include only necessary fields in commands and summaries.

## Out of scope

Do not create, edit, apply, delete, share, or restore dashboards, notebooks, workflows, settings, extensions, buckets, or other Dynatrace resources. If a request needs one of those operations, state that this skill supports read-only telemetry investigation only.
