---
name: dtctl
description: Answer Dynatrace service questions efficiently and investigate incidents with dtctl through read-only production and nonproduction contexts. Use for service health, request/error/latency checks, Davis problems, deployment validation, trends, error diagnosis, trace-to-log correlation, deployment symptoms, Kubernetes workload logs, and novel DQL authoring or repair.
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
| “Rundown,” “is it healthy?”, “at a glance,” “anything wrong?” | General metric fast path with all four measures | One scalar query; bounded application-presence fallback only when empty |
| “How many requests/failures?”, “what is the error rate?”, “what is p95/p99?” | General metric fast path with only the requested measure | One scalar query; bounded application-presence fallback only when empty |
| “Quick error summary,” “what is failing in this service?”, “summarize its errors” | Service error fast path | One totals query; bounded entity fallback only when empty; one ranking only when failures exist |
| “Any active problems?”, “what did Davis detect?”, “problem history” | Davis problem fast path | One entity query, then one bounded problem query |
| “When did Service Version X begin serving?”, deployment question without a trusted timestamp | Service Version timing fast path | One exact-version request timeline; preserve regional boundaries |
| “Validate this deployment,” “is the deployment healthy?”, “did this deployment cause the issue?” | Deployment validation | Verify the Service Version rollout range, then metrics, traces, and logs |
| “When did it spike?”, “by region/endpoint?”, “compare these windows” | One tailored metric timeline or comparison | One query first; no raw telemetry |
| Root cause, exact RID/request/trace, logs, spans, or deployment symptoms | Standard investigation | Metric-first, then selective raw telemetry |
| Write, fix, or optimize novel DQL | DQL authoring | Read only `references/dql-authoring.md`; execute once before verification |

This routing reflects the recurring question patterns behind the skill: broad health summaries, single aggregate facts, time or dimension comparisons, and exact incident drilldowns. Match explicit intent over keywords. A mention of “errors” alone is an aggregate metric question; “why are errors happening?” is an investigation.

## General metric fast path

Use the bundled runner for broad health summaries and single aggregate request, failure, error-rate, or latency questions. An environment plus an application name is a sufficient starting target; do not require the user to supply a tagged `service.name`, entity ID, or exact workload. Normalize a known logical application through [mappings.md](mappings.md), then pass its telemetry stem to the runner. If the supplied application name is already the mapped stem, do not read its service note, query-strategy reference, or raw-query reference before running the fast path.

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
4. If that query is empty, treats the result as missing standard APM metrics—not a missing application—and performs a capped 15-minute presence check using the environment plus application stem: paired `log.source`/`env` or exact tagged workload logs first, then exact tagged workload spans only if logs are empty.
5. Prints ready-to-send Markdown with the standard metrics or the application-presence evidence and one exact Dynatrace query link.

Run the command with normal network and macOS Keychain access when the execution sandbox requires it. Return its stdout directly and stop when it contains standard metrics or application-presence evidence. Do not add interpretation, another query, entity lookup, or a proof table unless the user asked for it. If the bounded fallback is inconclusive, read the mapped service note and [references/query-strategy.md](references/query-strategy.md), then continue with exact-name discovery; do not stop with an absence claim.

An empty metric series only proves that the metric selector had no points in that context and window. Never say or imply that an application, service, deployment, or workload does not exist based only on an empty metric, log, span, entity, or catalog query. State the selector and window that had no data, distinguish missing telemetry from nonexistence, and exhaust the supplied environment plus application identity before asking the user for another identifier.

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

The runner verifies the read-only context once and runs one request/failure query grouped by active service entity. When the tagged `service.name` selector returns nothing, it does not assume the service is absent: it performs a capped 15-minute span lookup by exact environment-qualified `k8s.workload.name`, then retries the metric query with every discovered `dt.entity.service`. Metric rows may also have null `service.name`; use the discovered workload name as their display identity. It stops when no failures exist; otherwise it runs one additional metric query that ranks failed requests by `endpoint.name` and `http.response.status_code`. It prints ready-to-send Markdown with exact counts, per-entity rates, direct links to the native **Services > Failures** analysis for each active entity, and one reproducible DQL breakdown link. A service entity or region is not a deployment version; never label these rows as deployments.

This is the default route for quick error analysis because it avoids raw log and span scans. Treat a missing HTTP status as unavailable metric enrichment, not as a successful request. Use the native Failure Analysis links for failed traces, contextual logs, outgoing calls, database failures, and comparison mode. Continue to the standard investigation only when the user asks why a specific failure occurred or the summary identifies a concrete incident that needs root-cause analysis.

Dynatrace documents the native UI in [Failure Analysis](https://docs.dynatrace.com/docs/observe/application-observability/services/failure-analysis): open **Services > Failures** for exploratory per-service failures, or use a problem's **Analyze failures** drill-down for pre-filtered incident context. **Problems** remains the incident-level impact and root-cause view.

## Davis problem fast path

Use the bundled problem runner for active problems, recent problem history, Davis
root-cause results, or blast radius:

```bash
python3 scripts/src/run_service_problem_summary.py \
  --environment prd --service sf-item --lookback 1d
```

Use `--status active` when the user asks only about current problems. The runner
uses one metric query to resolve exact service entities observed in the window
and one bounded problem query with a 5 GB cap. If no entity matches, it skips the problem query
instead of scanning the tenant. Return its stdout and stop unless the user asks
to explain a specific problem. For that drill-down, read
[references/davis-problems.md](references/davis-problems.md).

## Service Version timing fast path

When the prompt includes a Service Version or asks when a release actually
reached an environment, locate deployment traffic through the existing request
count metric before choosing a validation window:

```bash
python3 scripts/src/run_service_deployment_summary.py \
  --environment prd --service sf-item \
  --version 0.180.0 --lookback 14d
```

The runner filters `dt.service.request.count` by the exact
`primary_tags.version` value and groups by `service.name` so regional rollouts
remain separate. In validated Chewy telemetry, `primary_tags.version` carries
the Service Version (for example, `0.180.0`). Use the first nonzero request bucket
as the observed traffic rollout boundary at the reported interval precision.
This is stronger evidence of when
the deployed code began serving requests than an assumed timestamp, a service
entity creation time, or an unversioned traffic change.

Do not call an artifact publish time, merge time, pod start time, or midpoint in
a metric change the deployment time unless the user explicitly asks about that
event. State that the request metric proves the first observed traffic for the
exact Service Version, not the precise orchestration start. Treat staggered
regional boundaries separately. The verified deployment range begins at the
earliest regional first-request bucket and ends at the latest regional bucket
end. An empty exact-version series is inconclusive: confirm the literal Service
Version and widen the bounded lookback before saying that the version was not
observed; never turn it into a claim that the deployment or workload did not
exist.

## Deployment validation

Validate a deployment with a verified rollout range and evidence from metrics,
traces, and logs. Do not declare the service healthy from the metric threshold
check alone.

1. Run the Service Version timing fast path. Report the earliest regional
   first-request bucket through the latest regional bucket end as the observed
   deployment range, while retaining each region's boundary. If another explicit
   deployment event supplies the range, verify that versioned request traffic
   overlaps it; never invent a midpoint from an unversioned traffic change.
2. Compare guarded metric windows around each regional boundary. Use the bundled
   runner when the regional boundaries overlap closely enough for one service-wide
   comparison:

   ```bash
   python3 scripts/src/run_service_regression.py \
     --environment prd --service sf-item \
     --change-time 2026-08-20T14:30:00Z
   ```

   The default compares 30 minutes before and after with a five-minute guard and
   flags material request, error-rate, and p95-latency changes. For a staggered
   rollout, run tailored region-filtered comparisons rather than collapsing the
   boundaries.
3. Read [references/raw-query-controls.md](references/raw-query-controls.md), then
   inspect bounded root spans during and after the rollout. Include representative
   successful traffic plus slow or failed traces. Identify the first failing span
   and whether the failure originates in the deployed service or a downstream
   call; do not attribute a downstream failure to the caller merely because its
   request failed.
4. Inspect bounded logs for the deployed workloads during and after each regional
   boundary. Check new error signatures, crashes, restarts, and warnings, and use
   exact trace, pod, and time evidence to correlate logs with the selected traces.
   Inspect the implicated downstream workload's logs when a trace places the
   originating failure there.
5. Conclude healthy only when request volume, error rate, latency, representative
   traces, and bounded logs are consistent after the rollout. Treat unavailable
   telemetry as a validation gap, not evidence of health. Report the verified
   deployment range, every signal checked, regional differences, and direct
   Dynatrace links.

## Focused metric trend or breakdown

For a time trend, region or endpoint breakdown, or comparison, stay metric-only. Read [references/query-strategy.md](references/query-strategy.md), use `scripts/src/build_service_rundown_query.py` with only the requested `--metric`, confirmed low-cardinality `--group-by` fields, and an explicit interval, then execute that single query. Use `scripts/src/build_logs_events_graph_link.py` for a time-series link. Stop unless the result gives a concrete reason for a deeper investigation.

## Standard investigation

For debugging, root cause, exact records, logs, traces, or deployment symptoms:

1. Fix the environment, service, absolute window, and user timezone once.
2. Read [mappings.md](mappings.md) only to normalize the target, then read only its linked service note and [references/query-strategy.md](references/query-strategy.md). For novel DQL, also read [references/dql-authoring.md](references/dql-authoring.md).
3. Start with `dt.service.request.count` to locate traffic, failures, and the smallest useful incident window. For an error investigation, compare the failure onset with `primary_tags.version` transitions for the target service; temporal overlap is correlation, not proof of causation.
4. Inspect a representative failed trace and find the first span where the error originates. If it is a downstream service, resolve that service and compare its failure onset with its own Service Version rollout range as well as the caller's. Keep caller symptoms distinct from downstream origin evidence.
5. Query only the logs needed to test the target or downstream hypothesis. Read [references/raw-query-controls.md](references/raw-query-controls.md) before raw queries; read [references/trace-log-correlation.md](references/trace-log-correlation.md) only for correlation.
6. Generate source-native evidence links. Read [references/evidence-links.md](references/evidence-links.md), then route exact traces to Distributed Tracing, Synthetic monitors and executions to Synthetic, logs to a log-query view, and metric trends to the existing time-series graph view.
7. Stop as soon as the evidence answers the question. Return observed values, the exact UTC window, the Service Versions and rollout ranges checked, concise conclusions, and links beside the claims they support.

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
