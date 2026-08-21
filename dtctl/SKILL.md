---
name: dtctl
description: Answer general Dynatrace service questions efficiently and investigate specific incidents with dtctl through read-only production and nonproduction contexts. Use for service health, request/error/latency checks, trends and breakdowns, error diagnosis, trace-to-log correlation, deployment symptoms, and Kubernetes workload logs.
---

# Dynatrace investigation with dtctl

Use read-only Grail telemetry and return tenant-correct Dynatrace links. Treat `NOT_AUTHORIZED_FOR_TABLE` as the access boundary.

## Route the environment

| Target | Context | Environment URL |
| --- | --- | --- |
| `prd` | `prod` | `DTCTL_PROD_ENVIRONMENT` |
| `stg`, `qat`, `dev` | `nonprod` | `DTCTL_NONPROD_ENVIRONMENT` |

Keep both contexts at safety level `readonly`. Pass `--context` to every query and use the selected context URL for links.

## Route before querying

Choose the cheapest route that answers the prompt. Do not turn a general metric question into an incident investigation.

| Question shape | Route | Budget |
| --- | --- | --- |
| “Rundown,” “is it healthy?”, “at a glance,” “anything wrong?” | General metric fast path with all four measures | One scalar query |
| “How many requests/failures?”, “what is the error rate?”, “what is p95/p99?” | General metric fast path with only the requested measure | One scalar query |
| “Quick error summary,” “what is failing in this service?”, “summarize its errors” | Service error fast path | One totals query; one endpoint/status ranking only when failures exist |
| “When did it spike?”, “by region/endpoint?”, “compare these windows” | One tailored metric timeline or comparison | One query first; no raw telemetry |
| Root cause, exact RID/request/trace, logs, spans, or deployment symptoms | Standard investigation | Metric-first, then selective raw telemetry |

This routing reflects the recurring question patterns behind the skill: broad health summaries, single aggregate facts, time or dimension comparisons, and exact incident drilldowns. Match explicit intent over keywords. A mention of “errors” alone is an aggregate metric question; “why are errors happening?” is an investigation.

## General metric fast path

Use the bundled runner for broad health summaries and single aggregate request, failure, error-rate, or latency questions. If the user already supplied a tagged logical service or exact telemetry stem, do not read mappings, service notes, query-strategy references, or raw-query references.

For a broad health summary, run from this skill directory:

```bash
python3 scripts/src/run_service_rundown.py \
  --environment prd \
  --service sf-item \
  --lookback 1d
```

For a focused aggregate question, select only what was asked; repeat `--metric` only when the prompt asks for multiple measures:

```bash
# “How many requests did sf-item handle in production over the last hour?”
python3 scripts/src/run_service_rundown.py \
  --environment prd --service sf-item --lookback 1h \
  --metric requests

# “What was its p99 latency?”
python3 scripts/src/run_service_rundown.py \
  --environment prd --service sf-item --lookback 1h \
  --metric latency --latency-percentile 99
```

Available metric names are `requests`, `failures`, `error-rate`, and `latency`. Omit `--metric` only for a broad health summary. Match the user's timeframe; use `--end-time` when an absolute end is needed for exact reproduction.

The runner deterministically:

1. Resolves an absolute UTC window.
2. Verifies the matching context URL, `readonly` safety level, and reusable OAuth session.
3. Runs one bounded query containing only the selected measures and their required inputs.
4. Prints ready-to-send Markdown with one exact Dynatrace metric-query table link.

Run the command with normal network and macOS Keychain access when the execution sandbox requires it. Return its stdout directly and stop. Do not add interpretation, another query, logs, spans, entity lookup, a proof table, or a follow-up investigation unless the user asked for it.

Never create local or inline telemetry visualizations. Do not invoke client-side visualization, image generation, HTML rendering, screenshots, or browser/UI work. When the user explicitly asks for a time trend, return a Dynatrace time-series link generated from the exact query.

If authentication is unavailable, report the exact login command printed by the script and stop. The user can run that command manually; rerun the rundown after authentication succeeds.

## Service error fast path

Use the bundled error-summary runner when the user wants a quick explanation of what is failing, rather than only a failure count or a full root-cause investigation:

```bash
python3 scripts/src/run_service_error_summary.py \
  --environment prd \
  --service sf-item \
  --lookback 1d
```

The runner verifies the read-only context once and runs one request/failure query grouped by active service entity. It stops there when no failures exist; otherwise it runs one additional metric query that ranks failed requests by `endpoint.name` and `http.response.status_code`. It prints ready-to-send Markdown with exact counts, per-deployment rates, direct links to the native **Services > Failures** analysis for each active entity, and one reproducible DQL breakdown link.

This is the default route for quick error analysis because it avoids raw log and span scans. Treat a missing HTTP status as unavailable metric enrichment, not as a successful request. Use the native Failure Analysis links for failed traces, contextual logs, outgoing calls, database failures, and comparison mode. Continue to the standard investigation only when the user asks why a specific failure occurred or the summary identifies a concrete incident that needs root-cause analysis.

Dynatrace documents the native UI in [Failure Analysis](https://docs.dynatrace.com/docs/observe/application-observability/services/failure-analysis): open **Services > Failures** for exploratory per-service failures, or use a problem's **Analyze failures** drill-down for pre-filtered incident context. **Problems** remains the incident-level impact and root-cause view.

## Focused metric trend or breakdown

For a time trend, region or endpoint breakdown, or comparison, stay metric-only. Read [references/query-strategy.md](references/query-strategy.md), use `scripts/src/build_service_rundown_query.py` with only the requested `--metric`, confirmed low-cardinality `--group-by` fields, and an explicit interval, then execute that single query. Use `scripts/src/build_logs_events_graph_link.py` for a time-series link. Stop unless the result gives a concrete reason for a deeper investigation.

## Standard investigation

For debugging, root cause, exact records, logs, traces, or deployment symptoms:

1. Fix the environment, service, absolute window, and user timezone once.
2. Read [mappings.md](mappings.md) only to normalize the target, then read only its linked service note and [references/query-strategy.md](references/query-strategy.md).
3. Start with `dt.service.request.count` to locate traffic, failures, and the smallest useful incident window.
4. Query only the logs or spans needed to answer the explicit question. Read [references/raw-query-controls.md](references/raw-query-controls.md) before raw queries; read [references/trace-log-correlation.md](references/trace-log-correlation.md) only for correlation.
5. Generate source-native evidence links. Read [references/evidence-links.md](references/evidence-links.md), then route exact traces to Distributed Tracing, Synthetic monitors and executions to Synthetic, logs to a log-query view, and metric trends to the existing time-series graph view.
6. Stop as soon as the evidence answers the question. Return observed values, the exact UTC window, concise conclusions, and links beside the claims they support.

When a failed request yields a valid 32-character `trace.id`, immediately generate a bounded `dynatrace.distributedtracing/view-trace` intent link before continuing. Use the exact `trace.id` and incident timeframe; do not send exact-trace evidence to Logs and Events. Continue to query spans only when more analysis is needed:

```dql
fetch spans, from:"WINDOW-START", to:"WINDOW-END"
| filter trace.id == toUid("TRACE-ID")
| fields start_time, trace.id, span.id, parent_span.id, span.name, duration, span.status_code, dt.entity.service
| sort start_time asc
| limit 20
```

For independent deep-investigation branches, read [references/parallel-investigation.md](references/parallel-investigation.md).

## Query limits

- Add `--fetch-timeout-seconds 60` to every query.
- For `fetch logs` or `fetch spans`, apply a selective filter before sorting, return only needed fields, end with `limit 20`, and begin at `--default-scan-limit-gbytes 5`.
- Narrow a timed-out or capped query before raising its scan limit. Get approval for an unsampled raw window over two hours, a weak selector, a custom bucket, or a cap above 50 GB.
- Keep customer data, captured headers, secrets, and full log content out of links and summaries.
- Format every log query for people as well as machines: put `fetch logs` on the first line and every `|` pipeline command on its own subsequent line in commands, temporary DQL files, and links.

## Evidence links

Match the link destination to the evidence. Use `dtctl open intent` for app-native resources such as an exact trace or Synthetic monitor. Use `scripts/src/build_logs_events_link.py` for scalar metric summaries, logs, and other DQL record tables. Use `scripts/src/build_logs_events_graph_link.py` only when the user explicitly asks for a metric time trend. The graph helper preserves native time buckets and the time axis; never replace that visual evidence with a scalar table or client-rendered chart.

Keep the entire workflow read-only; dashboards, notebooks, workflows, settings, extensions, buckets, and other Dynatrace resources stay unchanged.
