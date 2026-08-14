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

Pass `--context "$DT_CONTEXT"` on every subsequent `dtctl` query and any failure-triggered verification; do not rely on the current default context. Require preconfigured read-only `nonprod` and `prod` contexts. If either context is unavailable or the user asks to refresh credentials, direct them to [README.md](README.md) instead of embedding workstation setup in the investigation workflow. Do not use `dtctl auth whoami`; it requires an OAuth/JWT identity scope that a platform token may not have.

Normalize the target into an environment tag, environment value, and telemetry stem before querying. For example, `[stg][use1]agentic-commerce-orchestrator` becomes `[stg]`, `stg`, and `agentic-commerce-orchestrator`. Read [mappings.md](mappings.md) for aliases such as `purchase-app` to `purchaseapp`.

Use one logical-service selector across regions on the happy path:

- Logs: `log.source == "TELEMETRY-STEM" and env == "ENVIRONMENT"`.
- Metrics: `startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM")`.

Keep this shared selector contract in `SKILL.md`. Service mapping files provide only the telemetry stem and environment-neutral service behavior; never hard-code an environment value or repeat the common log selector in a service mapping.

Group the first result by `k8s.workload.name` for logs or `service.name` for metrics and confirm that every returned value belongs to the requested environment and logical service. The selector may intentionally return both `use1` and `use2`; aggregate them in the same query when the user wants a cross-region total. If an unexpected workload or service name appears, switch to an explicit allowlist of the expected tagged names instead of silently including it.

Do not substitute `dt.entity.service.name` for the metric selector without inspecting it. In validated services, `dt.entity.service.name` was null on logs and request-count metric rows, and the custom `env` field was null on request-count metrics. The paired log fields and tagged metric `service.name` were the reliable selectors.

### Filter by region

Distinguish the deployment region (`use1`, `use2`) from the cloud region (`us-east-1`, `us-east-2`). Probe both namespaces before relating them; do not assume the mapping is universal.

- Metrics: filter deployment region through the tagged `service.name`, because the native `region` dimension can be null. Add `contains(service.name, "[REGION]")` to the logical metric selector and retain `service.name` in the first grouped result.
- Logs: keep `log.source` plus `env` as the logical-service selector. Filter deployment region with `contains(k8s.workload.name, "[REGION]")`; filter cloud region with `region == "CLOUD-REGION"` only after confirming it is populated.
- Spans: filter deployment region through the tagged `k8s.workload.name`; filter cloud region with `cloud.region == "CLOUD-REGION"` only after confirming it is populated. Do not rely on `dt.entity.service.name` for region selection.

When multiple regions are requested, query them together and group by the tagged service or workload field. Do not issue one happy-path query per region merely to add the results locally. Use an `or` expression only when the requested region set is narrower than all regions returned by the logical-service selector.

```bash
# One metric query for one deployment region; omit contains(...) to return every region.
dtctl --context "$DT_CONTEXT" query 'timeseries requests=sum(dt.service.request.count, scalar:true), by:{service.name}, filter:{startsWith(service.name, "[ENVIRONMENT]") and contains(service.name, "[REGION]") and endsWith(service.name, "]TELEMETRY-STEM")}, from:-15m | fields service.name, requests | limit 20' -o json --plain

# Logs by deployment region. Replace the workload filter with region == "CLOUD-REGION"
# only after a grouped probe confirms the cloud-region field.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-15m | filter log.source == "TELEMETRY-STEM" and env == "ENVIRONMENT" | filter contains(k8s.workload.name, "[REGION]") | fields timestamp, k8s.workload.name, region, loglevel, trace_id, span_id | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Spans by deployment region. Add cloud.region == "CLOUD-REGION" only after probing it.
dtctl --context "$DT_CONTEXT" query 'fetch spans, from:now()-15m | filter startsWith(k8s.workload.name, "[ENVIRONMENT]") and contains(k8s.workload.name, "[REGION]") and endsWith(k8s.workload.name, "]TELEMETRY-STEM") | fields start_time, k8s.workload.name, cloud.region, trace.id, span.id, span.name | sort start_time desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain
```

Resolve an exact telemetry service name to its entity ID only when the logical selector is absent or ambiguous, or when a span query requires `dt.entity.service`. Use the mapped entity ID as a seed; if it has no data in the selected context, run exact-name discovery. If more than one record matches, disambiguate before continuing.

```bash
dtctl --context "$DT_CONTEXT" query 'fetch dt.entity.service | filter entity.name == "SERVICE-NAME" | fields id, entity.name | limit 20' --default-scan-limit-gbytes 5 -o json --plain
```

An exact name can resolve to multiple active entities, including separate traffic classes under one workload. Rank candidates over the investigation window with `dt.service.request.count`; inspect pod, process, or workload identity in a small span sample when more than one candidate remains active. Do not select the first entity arbitrarily, and retain multiple IDs when the question spans multiple traffic classes.

```bash
dtctl --context "$DT_CONTEXT" query 'timeseries requests=sum(dt.service.request.count), interval:1h, by:{dt.entity.service, service.name}, filter:{service.name == "EXACT-TAGGED-SERVICE"}, from:-24h | fields dt.entity.service, service.name, requests_total=arraySum(requests) | sort requests_total desc | limit 20' -o json --plain
```

## Find traffic and failures cheaply first

Use `dt.service.request.count` before fetching logs or spans for a logical service. Metrics are substantially cheaper for locating traffic and failure hotspots; raw telemetry is for classifying errors and retrieving representative evidence.

Do not assume that failures use a separate metric key. Inspect the metric catalog for the logical service first. In span-derived service metrics, `dt.service.request.count` can expose a boolean `failed` dimension plus dimensions such as `endpoint.name`. Treat dimensions as tenant- and service-specific: use only fields returned by the catalog query.

Skip the metric step only when the user already supplied an exact trace/request ID with a narrow window, or when the target has no request-count metric. In the latter case, use the logical log selector or exact workload and apply the raw-data sampling workflow below for a large requested range.

```bash
# Recent activity at one-minute resolution across the environment's regions.
dtctl --context "$DT_CONTEXT" query 'timeseries requests=sum(dt.service.request.count), interval:1m, by:{service.name}, filter:{startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM")}, from:-15m | fields timeframe, interval, service.name, requests | limit 20' -o json --plain

# A historical window at coarse resolution.
dtctl --context "$DT_CONTEXT" query 'timeseries requests=sum(dt.service.request.count), interval:15m, filter:{startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM")}, from:-24h | fields timeframe, interval, requests | limit 20' -o json --plain

# Discover whether request count exposes failure and ranking dimensions.
dtctl --context "$DT_CONTEXT" query 'metrics | filter metric.key == "dt.service.request.count" | filter startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM") | fields metric.key, failed, endpoint.name, dt.entity.service, service.name, dt.metrics.source | dedup service.name, failed, endpoint.name | sort service.name asc, failed desc, endpoint.name asc | limit 100' -o json --plain

# Find failure hotspots across a large requested range without scanning raw spans or logs.
dtctl --context "$DT_CONTEXT" query 'timeseries failures=sum(dt.service.request.count), interval:1h, filter:{startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM") and failed == true}, from:-7d | fields timeframe, interval, failures | limit 20' -o json --plain

# Rank metric dimensions across the requested range. Replace endpoint.name only with a
# dimension confirmed by the metric-catalog query.
dtctl --context "$DT_CONTEXT" query 'timeseries failures=sum(dt.service.request.count), interval:1h, by:{endpoint.name}, filter:{startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM") and failed == true}, from:-7d | fieldsAdd failures_total=arraySum(failures) | fields endpoint.name, failures_total | sort failures_total desc | limit 20' -o json --plain
```

Use the metric in this order:

1. Match its timeframe to the user's requested investigation window.
2. Inspect `metrics` for the logical selector to discover `failed` and available grouping dimensions. Keep `service.name` in the first result to verify regional membership.
3. For error investigations, chart `failed == true` at a resolution appropriate to the range: one minute for short incidents, 15 minutes for day-scale windows, and one hour or coarser for week-scale windows.
4. Rank confirmed dimensions such as `endpoint.name` by total failures. Use request volume as a denominator when the question concerns failure rate rather than failure count.
5. For one incident, refine a peak interval to one-minute resolution and drill into it. For analysis over a large time range, retain the requested range and use the sampling workflow below before selecting narrower examples.

The `failed` metric dimension represents failed service requests derived from spans; it is not a count of `ERROR` log records. Likewise, `endpoint.name` can describe an inbound operation rather than a downstream service or GraphQL subgraph. Do not relabel an endpoint as a subgraph unless telemetry establishes that mapping. Use metrics for exact counts, rates, rankings, and time selection; use sampled spans or logs to identify error types and supporting examples.

If the metric has no data, do not conclude that no logs exist. Probe the paired `log.source` and `env` selector, then retry with the exact Kubernetes workload if those fields are absent. Keep a short incident window bounded, or sample across the full range for a large-range analysis.

## Required query controls

Every `fetch logs` or `fetch spans` query must:

1. Use either a small metric-selected incident window or an explicit sampling ratio over a large user-requested analysis window.
2. Filter on a selective target such as paired `log.source` plus `env`, an exact `dt.entity.service`, `trace_id`, `trace.id`, `k8s.namespace.name`, `k8s.workload.name`, or `host.name` before sorting or aggregation.
3. Return only fields needed for the next step and end with `limit 20` (never over 100 without a reason).
4. Use `-o json --plain`. Start the first raw telemetry query of every new investigation with `--default-scan-limit-gbytes 5`; use a higher cap only after following the escalation workflow below.

A result limit does not limit Grail scan cost. A request-count metric can locate failures across a broad window without scanning raw telemetry.

When a necessary query reaches its scan cap:

1. Confirm that its target, timeframe, fields, sorting, and aggregation are still needed for the question. Use the failure metadata or partial result to judge whether the query was close to completing.
2. Reduce avoidable scan cost first: strengthen selectors, reuse a metric-selected interval, remove unnecessary fields or operations, or increase sampling for large-range classification. Do not make the query cheaper in a way that prevents it from answering the user's question.
3. If the query remains necessary, raise the cap by the smallest useful step. Prefer `5` to `10` to `20`, then 10 GB increments up to `50`; use a smaller intermediate value when the evidence supports it. Do not jump directly from 5 GB to 50 GB merely for convenience.
4. Stop escalating as soon as the query succeeds or the likely value no longer justifies the added cost. Do not repeat an unchanged capped query without changing either its shape, sampling ratio, or cap.
5. Reuse the lowest proven-sufficient cap only for closely related follow-up queries in the same investigation. Start a separate investigation back at 5 GB instead of treating a previous higher cap as a new default.

Use judgment rather than treating 50 GB as a target or budget. Before an **unsampled** raw `fetch logs` or `fetch spans` window over two hours, a weakly filtered fetch, a custom bucket, or a scan cap over 50 GB, explain the cost and get the user's approval first. Never exceed 50 GB without explicit approval.

## Sample raw errors over large ranges

When the user asks to analyze or rank errors over a large time range, do not answer from only the latest or busiest minute. Keep the requested timeframe and introduce sampling after the metric pass:

1. Run the raw query over the full requested range with `--default-sampling-ratio 10` and the 5 GB starting cap. Use powers of ten and increase the ratio to `100`, `1000`, or higher if that cap is reached; use the incremental scan-cap workflow only when stronger sampling would undermine the needed evidence.
2. Include `--metadata=scannedBytes,sampled,analysisTimeframe` and confirm `sampled` is `true` and `analysisTimeframe` matches the requested range.
3. Use the full-range sample to discover error schemas, recurring types, and candidate subgraph or dependency fields.
4. Stratify follow-up evidence using the metric timeline: sample at least a peak-failure interval and a normal-baseline interval; for multi-day ranges also cover early and late portions or relevant deployment boundaries.
5. Use exact metrics for totals and rates. Label counts or rankings computed from sampled raw records as approximate, state the sampling ratio, and do not extrapolate rare-error counts unless the sampling design supports it.
6. After classifying error types, use selective exact fields such as endpoint, subgraph, error type, trace ID, or pod to retrieve small unsampled examples when needed.

Sampling reduces scan cost while preserving coverage of the requested period. If a sampled query still reaches the cap, increase the sampling ratio before raising the cap or narrowing the timeframe. Raise the cap incrementally only when stronger sampling would make the needed evidence unreliable. Narrow the timeframe only for incident drilldown, exact examples, or when sampling cannot answer the question.

```bash
# Sample error logs across a large requested range. Use the exact service entity when
# log enrichment is reliable; otherwise use the exact workload.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-7d | filter k8s.workload.name == "EXACT-WORKLOAD" | filter loglevel == "ERROR" | fields timestamp, content, trace_id, span_id, k8s.pod.name | sort timestamp desc | limit 20' --default-sampling-ratio 100 --default-scan-limit-gbytes 5 --metadata=scannedBytes,sampled,analysisTimeframe -o json --plain

# Approximate a top list only after discovering structured fields in the sample.
# Replace the placeholders with fields actually present in the sampled telemetry.
dtctl --context "$DT_CONTEXT" query 'fetch spans, from:now()-7d | filter dt.entity.service == "SERVICE-xxx" | filter span.status_code == "ERROR" | summarize sampled_errors=count(), by:{`DISCOVERED-SUBGRAPH-FIELD`, `DISCOVERED-ERROR-TYPE-FIELD`} | sort sampled_errors desc | limit 20' --default-sampling-ratio 100 --default-scan-limit-gbytes 5 --metadata=scannedBytes,sampled,analysisTimeframe -o json --plain
```

Sampling can miss rare events and can distort rankings when records have unequal inclusion behavior. Present sampled raw results as classification evidence, not exact population counts. If the metric catalog already exposes the desired grouping dimension, prefer its exact metric ranking over a sampled raw aggregation.

Execute DQL directly on the normal path. Do not run `dtctl verify query` as a routine preflight, even for unfamiliar DQL; it adds a redundant request when the query is already valid.

Use verification only after `dtctl query` fails with an error that identifies the DQL as invalid, such as a syntax, type, function, field, or semantic validation error. Do not verify authorization failures, scan-limit failures, transport errors, missing data, or valid queries that return no records.

When an invalid-query error occurs:

1. Run `dtctl verify query` on the exact failed DQL in the same context.
2. Read the complete verifier output and use its locations, suggestions, and diagnostic codes to identify the smallest correction. Treat `SEVERE` or `QUERY_ALWAYS_EMPTY_FILTER` as validation failures even when the verifier also prints `Query is valid` and exits successfully.
3. Execute the corrected query once with its original output, scan-limit, sampling, and metadata controls. Do not rerun the unchanged invalid query or verify the corrected query preemptively.

For example, only run the second command after the first command reports invalid DQL:

```bash
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-15m | filter dt.entity.service == "SERVICE-xxx" | limit 20' --default-scan-limit-gbytes 5 -o json --plain
dtctl --context "$DT_CONTEXT" verify query 'fetch logs, from:now()-15m | filter dt.entity.service == "SERVICE-xxx" | limit 20' --plain
```

## Correlate logs and traces

Start from the logical log selector and inspect the structured correlation fields in the metric-selected window. If no logs appear, retry with the exact workload. Resolve a service entity only when the next span query needs it. Do not assume log and span field names are identical or populated.

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
dtctl --context "$DT_CONTEXT" query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter trace.id == toUid("TRACE-ID") | fields start_time, trace.id, span.id, parent_span.id, span.name, duration, span.status_code, dt.entity.service | sort start_time asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Find all logs carrying that exact trace ID, including other services when present.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:"WINDOW-START", to:"WINDOW-END" | filter trace_id == "TRACE-ID" | fields timestamp, loglevel, trace_id, span_id, dt.entity.service, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# When native IDs are absent, map one selected span to logs by exact pod and a tight
# interval computed locally from span start_time, duration, and a small clock-skew margin.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:"SPAN-START-MINUS-SKEW", to:"SPAN-END-PLUS-SKEW" | filter k8s.pod.name == "SPAN-POD" | fields timestamp, loglevel, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Find HTTP root spans with a captured X-Request-ID header in one narrow window.
dtctl --context "$DT_CONTEXT" query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter dt.entity.service == "SERVICE-xxx" | filter request.is_root_span == true | filter isNotNull(`http.request.header.x-request-id`) | fields start_time, trace.id, span.id, span.name, span.kind, `http.request.header.x-request-id`, http.request.method, http.route, k8s.pod.name | sort start_time desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain
```

Log `trace_id` is a string, while span `trace.id` is a UID. Before using `toUid("TRACE-ID")`, confirm the log value is a 32-character hexadecimal trace UID; some applications populate `trace_id` with a shorter request or transaction identifier. Treat those values as application-local correlation keys, not trace IDs. Spans use `start_time`, while logs use `timestamp`. Correlate records locally by exact trace ID and then exact span ID. Use time only to order exact matches or as the explicitly labeled fallback when native IDs are absent. Do not force a server-side join unless separate bounded pivots are insufficient, because a join can substantially increase scan cost. Include `content` only when the message text is necessary; it can contain customer or request data.

Captured HTTP headers use the `http.request.header.<lowercase-name>` namespace and can be arrays. For X-Request-ID, query the backticked field `http.request.header.x-request-id`; do not assume top-level `x-request-id` or `request_attribute.x-request-id` is populated. Treat captured header values as sensitive and omit their values from summaries unless the user explicitly needs them.

If the span query returns `NOT_AUTHORIZED_FOR_TABLE`, report that trace data could not be inspected with the current identity. Continue with the log-side `trace_id` pivot when it still answers part of the question, and state clearly that this is correlation evidence from logs rather than verified span data.

If both structured correlation fields and message-level trace/span markers are absent, continue the log investigation using exact workload, pod, and timestamp filters. Report that log-to-trace correlation is unavailable for the sampled records; do not infer that the service emits no traces.

### Known service mappings

Normalize the target to a logical service name by removing its leading environment and region tags; for example, normalize `[stg][use1]agentic-commerce-notifier` to `agentic-commerce-notifier`. Use [mappings.md](mappings.md) to obtain the telemetry stem. Use that stem directly with paired `log.source` and `env` filters, or as the suffix of the tagged metric `service.name`.

Use the row's entity ID only as a fallback discovery seed in the `prod` or `nonprod` context already selected from the original environment tag. Keep one environment- and region-neutral mapping list, but validate the seed against current telemetry: live entity IDs can differ by context, region, deployment lineage, or traffic class. Run exact-name discovery when a span query needs an entity and no mapping exists, the seed returns no data, the exact name has multiple active IDs, or current telemetry conflicts with the mapping. Read only the linked logical-service file and re-probe its assumptions in the target environment.

## Other useful patterns

```bash
# Recent errors for one logical service across regions.
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-15m | filter log.source == "TELEMETRY-STEM" and env == "ENVIRONMENT" | filter loglevel == "ERROR" | fields timestamp, content, trace_id, span_id, k8s.workload.name, k8s.pod.name | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# A Kubernetes workload during a specific incident window
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-30m | filter k8s.namespace.name == "namespace" | filter k8s.workload.name == "workload" | fields timestamp, loglevel, content, trace_id, span_id, k8s.pod.name | sort timestamp desc | limit 20' --default-scan-limit-gbytes 5 -o json --plain

# Failed-request trend for one logical service; prefer this metric over scanning logs.
dtctl --context "$DT_CONTEXT" query 'timeseries failures=sum(dt.service.request.count), interval:5m, filter:{startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM") and failed == true}, from:-1h | fields timeframe, interval, failures | limit 20' -o json --plain
```

Use paired logical-service fields, a known entity ID, or an exact workload/namespace; do not begin with a tenant-wide text search. Treat telemetry as potentially sensitive and include only necessary fields in commands and summaries.

## Out of scope

Do not create, edit, apply, delete, share, or restore dashboards, notebooks, workflows, settings, extensions, buckets, or other Dynatrace resources. If a request needs one of those operations, state that this skill supports read-only telemetry investigation only.
