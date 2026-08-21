# Query strategy

Use this reference for target normalization, region selection, entity resolution, and metric-first incident discovery.

## Logical-service selectors

Normalize a tagged target such as `[stg][use1]agentic-commerce-orchestrator` into environment tag `[stg]`, environment value `stg`, deployment region `use1`, and telemetry stem `agentic-commerce-orchestrator`. Read `../mappings.md`, then only the linked logical-service file.

Use one selector across regions on the happy path:

- Logs: `log.source == "TELEMETRY-STEM" and env == "ENVIRONMENT"`.
- Metrics: `startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM")`.

Group the first result by `k8s.workload.name` for logs or `service.name` for metrics. Confirm every value belongs to the requested environment and logical service. If an unexpected value appears, switch to an explicit allowlist.

Do not substitute `dt.entity.service.name` without inspecting it. In validated services it was null on logs and request-count metric rows; custom `env` was null on request-count metrics. Paired log fields and tagged metric `service.name` were reliable.

## Region filters

Distinguish deployment region (`use1`, `use2`) from cloud region (`us-east-1`, `us-east-2`). Probe both namespaces before relating them.

- Metrics: filter deployment region with `contains(service.name, "[REGION]")`; native `region` can be null.
- Logs: retain the logical selector and use `contains(k8s.workload.name, "[REGION]")`. Use `region == "CLOUD-REGION"` only after confirming it is populated.
- Spans: filter deployment region through tagged `k8s.workload.name`; use `cloud.region` only after probing it.

Query multiple requested regions together and group by tagged service or workload. Do not run one happy-path query per region merely to add results locally.

```bash
dtctl --context "$DT_CONTEXT" query 'timeseries requests=sum(dt.service.request.count, scalar:true), by:{service.name}, filter:{startsWith(service.name, "[ENVIRONMENT]") and contains(service.name, "[REGION]") and endsWith(service.name, "]TELEMETRY-STEM")}, from:-15m | fields service.name, requests | limit 20' --fetch-timeout-seconds 60 -o json --plain

dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-15m
| filter log.source == "TELEMETRY-STEM" and env == "ENVIRONMENT"
| filter contains(k8s.workload.name, "[REGION]")
| fields timestamp, k8s.workload.name, region, loglevel, trace_id, span_id
| sort timestamp desc
| limit 20' --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain
```

## Resolve entity IDs only when needed

Resolve an exact telemetry service name only when the logical selector is absent or ambiguous, or the next span query requires `dt.entity.service`. Treat mapped IDs as discovery seeds and verify current telemetry.

```bash
dtctl --context "$DT_CONTEXT" query 'fetch dt.entity.service | filter entity.name == "SERVICE-NAME" | fields id, entity.name | limit 20' --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain
```

Exact names can resolve to multiple active entities or traffic classes. Rank candidates over the requested window with `dt.service.request.count`; never choose the first arbitrarily.

```bash
dtctl --context "$DT_CONTEXT" query 'timeseries requests=sum(dt.service.request.count), interval:1h, by:{dt.entity.service, service.name}, filter:{service.name == "EXACT-TAGGED-SERVICE"}, from:-24h | fields dt.entity.service, service.name, requests_total=arraySum(requests) | sort requests_total desc | limit 20' --fetch-timeout-seconds 60 -o json --plain
```

## Find traffic and failures cheaply

Use `dt.service.request.count` before raw logs or spans unless the user supplied an exact trace/request ID and narrow window, or the service has no request-count metric.

For a basic service rundown or focused aggregate metric question, run the scalar workflow from the skill directory:

```bash
python3 scripts/src/run_service_rundown.py \
  --environment prd \
  --service sf-item \
  --lookback 1d
```

It performs context preflight, runs one scalar request/error/latency query, and emits ready-to-send Markdown with a table-style Dynatrace link. Stop there for summary requests.

For a quick summary of what is failing, use the dedicated error runner instead of manually issuing totals, endpoint, region, log, and span queries:

```bash
python3 scripts/src/run_service_error_summary.py \
  --environment prd \
  --service sf-item \
  --lookback 1d
```

It aggregates request and failure totals across the logical service, preserves each active entity for native Services Failure Analysis links, and ranks the top failing endpoint/status groups across regions. It performs the ranking query only when failures are present. If the tagged `service.name` selector is empty, let the runner perform its capped workload-span lookup and entity-ID metric retry; do not treat null `service.name` as an absent service. Do not add other raw telemetry unless the user asks for root cause or a specific failed request.

Select only the requested measure for a focused question. This avoids calculating response-time percentiles for request-count questions or request/error measures for latency-only questions:

```bash
python3 scripts/src/run_service_rundown.py \
  --environment prd \
  --service sf-item \
  --lookback 1h \
  --metric requests

python3 scripts/src/run_service_rundown.py \
  --environment prd \
  --service sf-item \
  --lookback 1h \
  --metric latency \
  --latency-percentile 99
```

For a requested regional, endpoint, or time-series follow-up, build a bounded timeline with confirmed low-cardinality dimensions:

```bash
python3 scripts/src/build_service_rundown_query.py \
  --environment prd \
  --service sf-item \
  --from-time 2026-08-20T20:00:00Z \
  --to-time 2026-08-20T21:00:00Z \
  --interval 5m \
  --metric requests \
  --group-by service.name \
  --additional-filter 'contains(service.name, "[use1]")'
```

Use only dimensions already confirmed for the metrics. Preserve those dimensions in each graph projection. Keep secrets and customer identifiers out of additional filters and output links.

For a broad traffic or performance review, preserve metric arrays so Logs and Events Classic can render a time-series bar chart with time on the x-axis. Group by region-bearing `service.name` unless another low-cardinality dimension directly answers the prompt, and select an explicit interval appropriate to the requested window:

```bash
dtctl --context "$DT_CONTEXT" query 'timeseries requests=sum(dt.service.request.count), interval:15m, by:{service.name, failed}, filter:{startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM")}, from:"WINDOW-START", to:"WINDOW-END", nonempty:true | sort service.name asc, failed asc' --fetch-timeout-seconds 60 -o json --plain
```

Generate this successful timeline with `scripts/src/build_logs_events_graph_link.py`. For performance prompts, return time-bucketed latency percentile arrays at an explicit interval; for error-rate prompts, group request timelines by the confirmed `failed` dimension. Compute headline totals and rates from the returned arrays for prose without adding scalar reductions to the linked graph DQL. Use separate graphs when request volume and latency/error-rate scales would obscure each other.

For incident discovery, run the selective failure timeline and metric-catalog discovery concurrently after context/auth succeeds:

```bash
dtctl --context "$DT_CONTEXT" query 'timeseries requests=sum(dt.service.request.count), interval:1m, by:{service.name, failed, endpoint.name}, filter:{startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM")}, from:"WINDOW-START", to:"WINDOW-END" | fields timeframe, interval, service.name, failed, endpoint.name, requests | limit 100' --fetch-timeout-seconds 60 -o json --plain

dtctl --context "$DT_CONTEXT" query 'metrics | filter metric.key == "dt.service.request.count" | filter startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM") | fields metric.key, failed, endpoint.name, dt.entity.service, service.name, dt.metrics.source | dedup service.name, failed, endpoint.name | sort service.name asc, failed desc, endpoint.name asc | limit 100' --fetch-timeout-seconds 60 -o json --plain
```

Use only dimensions returned by catalog discovery. The `failed` dimension represents failed service requests derived from spans, not ERROR log counts. `endpoint.name` can be an inbound operation, not a downstream service or subgraph.

For short incidents use one-minute resolution; for day-scale windows use roughly 15 minutes; for week-scale windows use one hour or coarser. Rank confirmed dimensions by total failures and include request volume when the question concerns a rate.

Once a failure minute is known, query the root span immediately. When it returns a valid incident trace ID, stop and follow the top-level early-link rule before further drilldown.

If metrics have no data, do not conclude that logs are absent or that the application does not exist. For a general rundown, let `run_service_rundown.py` perform its capped application-presence fallback. Otherwise probe the paired logical log selector, then retry with the environment-qualified workload name when enrichment is missing. An empty presence probe remains inconclusive; state the selector and window, then use the mapped telemetry stem, service note, and exact tagged workload before asking the user for another identifier or making any existence claim.

## Other bounded patterns

```bash
# Recent errors for one logical service
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-15m
| filter log.source == "TELEMETRY-STEM" and env == "ENVIRONMENT"
| filter loglevel == "ERROR"
| fields timestamp, content, trace_id, span_id, k8s.workload.name, k8s.pod.name
| sort timestamp desc
| limit 20' --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain

# Failed-request trend
dtctl --context "$DT_CONTEXT" query 'timeseries failures=sum(dt.service.request.count), interval:5m, filter:{startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]TELEMETRY-STEM") and failed == true}, from:-1h | fields timeframe, interval, failures | limit 20' --fetch-timeout-seconds 60 -o json --plain
```
