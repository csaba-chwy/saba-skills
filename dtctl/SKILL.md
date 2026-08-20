---
name: dtctl
description: Investigate Dynatrace services with dtctl using the correct nonprod or prod context, a visual metric-only fast path for quick service rundowns, metric-first failure discovery, safe bounded log and trace queries, early trace-query links, and parallel evidence collection. Use for quick health summaries, error analysis, trace-to-log correlation, deployment symptoms, Kubernetes workload logs, service latency, and service-specific observability investigations over short or long time ranges.
---

# Dynatrace investigation with dtctl

Use this skill for read-only Grail investigations. Never mutate Dynatrace resources. Treat `NOT_AUTHORIZED_FOR_TABLE` as a permission boundary; do not work around it or switch tools implicitly.

## Non-negotiable contract

- Select the `prod` context with `DTCTL_PROD_ENVIRONMENT` only for `[prd]`; select the `nonprod` context with `DTCTL_NONPROD_ENVIRONMENT` for `[stg]`, `[qat]`, and `[dev]`. If the environment is not explicit, ask. Never cross the production boundary as a fallback.
- Authenticate the selected environment with browser-based OAuth into its matching `prod` or `nonprod` context. Do not use any other context name, platform-token environment variables, or `dtctl config set-credentials`.
- Always create or refresh both contexts with `--safety-level readonly`. This is mandatory for production and must not be relaxed for nonproduction.
- Pass `--context "$DT_CONTEXT"` on every `dtctl` command. Confirm the context URL and auth before querying.
- Use the context environment URL as the only tenant source. Never guess or reuse a hostname from another context.
- Start with request metrics, then narrow raw logs or spans to a selective target and a metric-selected or explicitly bounded window.
- Back every material conclusion with observed values, the exact context and DQL, and a direct Dynatrace link whose visualization matches the evidence shape.
- Do not use Chrome or another browser on the normal path. Provide every evidence link as a raw, multiline DQL query in the classic Logs and Events app with Advanced mode enabled. Every metric graph must preserve native time buckets and render time on the x-axis; use tables for discrete records and categorical scalar summaries. Never route evidence through the Logs app, notebooks, dashboards, the distributed-trace view, or the single-log-entry view.
- Keep secrets, customer data, full log content, and sensitive captured headers out of URLs and summaries.

## Start safely

Normalize the target into its environment tag, environment value, and telemetry stem. Read [mappings.md](mappings.md), then read only the linked file under `services/` for the requested logical service.

```bash
case "$SERVICE_NAME" in
  "[prd]"*) DT_CONTEXT=prod; DT_ENVIRONMENT="$DTCTL_PROD_ENVIRONMENT" ;;
  "[stg]"*|"[qat]"*|"[dev]"*) DT_CONTEXT=nonprod; DT_ENVIRONMENT="$DTCTL_NONPROD_ENVIRONMENT" ;;
  *) print -u2 'Cannot determine Dynatrace context from service name'; exit 1 ;;
esac
[[ "$DT_ENVIRONMENT" == https://* ]] || { print -u2 'Selected Dynatrace environment is not configured as an https URL'; exit 1; }
dtctl auth login \
  --context "$DT_CONTEXT" \
  --environment "$DT_ENVIRONMENT" \
  --safety-level readonly
dtctl config describe-context "$DT_CONTEXT" --plain
dtctl --context "$DT_CONTEXT" auth status --plain
```

Confirm that the environment reported by `describe-context` exactly matches `DT_ENVIRONMENT` before querying. Never bind the `prod` context to the nonproduction URL or the `nonprod` context to the production URL. If OAuth or a keychain-backed credential is unavailable only inside the restricted execution environment, retry the same command once with normal browser and Keychain access rather than changing tools or authentication. Once that retry proves the context uses macOS Keychain credentials, run every later `dtctl` command with normal Keychain access on its first attempt. Do not incur a restricted-environment failure and approval wait for every query.

## Apply the shared service baseline

Treat each file under `services/` as a small set of service-specific overrides to this baseline, not a complete investigation recipe:

- Re-probe current telemetry before relying on a dated enrichment observation. Use the logical selectors first. Resolve an exact tagged service or workload only when a logical selector is absent or ambiguous, and rank duplicate entities by current request traffic.
- Inspect the dimensions actually returned by `dt.service.request.count`. Common dimensions include `failed`, `endpoint.name`, HTTP method and status, workload, and version, but partially enriched operations can omit some of them.
- Probe log service, entity, trace, and span fields before choosing a correlation mode. A native trace ID is 32 hexadecimal characters and a native span ID is 16 hexadecimal characters; shorter values are application-local keys. Use exact native IDs only when the sampled values validate them, otherwise use exact workload, pod, and a tight time window as supporting evidence.
- Expect spans to expose pod and workload identity plus server, client, or internal activity. Root spans can expose routes and X-Request-ID, but neither is guaranteed; treat captured request headers as sensitive.
- When a service note names a Grail log bucket, add `bucket:"BUCKET-NAME"` to every `fetch logs` query for that service. Keep the paired `log.source` and `env` filter as the logical selector even when the bucket narrows the scan.

## Quick rundown fast path

Treat prompts such as “quick rundown,” “rundown,” “quick health check,” “at a glance,” or “how has this service looked?” as summary requests unless the user explicitly asks for debugging, root cause, an incident investigation, exact records, logs, or traces. This fast path takes precedence over the broader workflow below.

1. Resolve and authenticate the target safely, fix an absolute window and interval, then use `scripts/src/build_service_rundown_query.py` to build one DQL query for request count, error rate, and p95 latency over time. Run that query with `dtctl`; do not hand-copy or independently align three metric results.
2. Default to a compact inline visualization with three aligned time-series panels: request count, error rate in percent, and p95 latency in milliseconds. Use the returned `timeframe`, `interval`, and metric arrays as the only plotted data. Label the target, absolute window, interval, units, and any grouping dimensions; do not make the user open Dynatrace to understand the basic trend.
3. Keep the default query aggregated across the logical service. Adapt a follow-up through the builder's interval, latency-percentile, `--group-by`, and pipeline-free `--additional-filter` options for a region, endpoint, failure class, or other confirmed low-cardinality dimension. Preserve the three baseline measures unless the user explicitly narrows the requested output.
4. When direct Dynatrace proof is useful, pass the same plot-ready DQL to `scripts/src/build_logs_events_graph_link.py` so the evidence link preserves the aligned arrays and renders time on the x-axis. Use at most one additional simple metric query when a scalar total or regional comparison materially improves the prose; present a categorical scalar result as prose or a table, never as a graph.
5. Do not query raw logs or spans, resolve entity IDs, start trace correlation, or use subagents on the fast path. If the metrics show failures, latency degradation, or another concern, state it plainly but stop before root-cause work.
6. Return the visualization, the timeframe, two or three headline observations, and at most one evidence link. Do not add a proof table unless it is necessary to prevent ambiguity.
7. End with one focused question offering a deeper follow-up, for example: “Want me to split this by region or endpoint, or drill into the latency spike?” Do not continue the investigation until the user chooses a direction.

## Investigation workflow

1. Resolve the target, context, absolute requested timeframe, and timezone interpretation once.
2. Choose the evidence shape from the request:
   - For aggregate traffic, performance, throughput, latency, or error-rate prompts over a range such as the last day, query bounded metrics with an explicit interval and publish time-series bar-chart links whose x-axis is time. Keep series selective enough to read, normally one series per region, endpoint class, failure state, or percentile.
   - For one RID, request ID, trace ID, or isolated request, query the exact bounded span and correlated log records and publish table links. Do not substitute a broad graph for the specific trace or log evidence.
3. For standard or deep investigations, use `dt.service.request.count` to locate traffic, failures, regions, and the smallest useful incident window. Run independent metric timeline and catalog queries concurrently.
4. For broad metric reviews, generate each successful time-series graph immediately and explain totals, rates, and percentiles in plain language. Preserve native metric arrays, `timeframe`, and `interval` in graph DQL; never collapse a graph into categorical scalar rows.
5. For incidents, query the root span or other most selective source needed to identify a representative failed trace and **immediately publish the trace-query link** using the rule below.
6. Run trace topology, log correlation, and comparator/downstream-health work in parallel when those branches are independent.
7. Synthesize only returned evidence, distinguish exact native correlation from pod/time support, and include linked proof beside every material claim.

Read [references/query-strategy.md](references/query-strategy.md) before constructing service, region, metric, or entity selectors.

## Publish a trace-query link immediately

As soon as any query returns a valid 32-character hexadecimal `trace.id` that supports the incident, create a selective, bounded `fetch spans` DQL query for that trace and publish it through the Logs & Events DQL view described in [references/evidence-links.md](references/evidence-links.md). Send the link to the user in commentary without waiting for log correlation, root-cause synthesis, comparison work, other evidence links, or the final answer.

```dql
fetch spans, from:"WINDOW-START", to:"WINDOW-END"
| filter trace.id == toUid("TRACE-ID")
| fields start_time, trace.id, span.id, parent_span.id, span.name, duration, span.status_code, dt.entity.service
| sort start_time asc
| limit 20
```

Confirm that the hostname matches the selected context and that decoding the Logs and Events fragment preserves the exact DQL, line breaks, absolute timeframe, and trace ID. Use a descriptive Markdown link such as `[Query the failed trace in Dynatrace](URL)`, state the observed status/duration already returned, and say that investigation is continuing. Keep the same link in the final evidence table.

If link generation fails, report the exact trace ID as **unlinked interim evidence** and continue; do not imply that a working link exists.

## Parallel drilldown

Use subagents when a standard or deep investigation has independent read-only branches and execution slots are available. Never use them for the quick rundown fast path. The coordinator owns the context, absolute timeframe, selector, initial metric pass, early user-facing trace link, and final synthesis.

After the incident window or trace ID is known, assign up to three non-overlapping lanes:

1. **Trace topology:** failing span chain, first failed dependency, and causal boundary.
2. **Logs:** native trace/span correlation or tightly bounded pod/time supporting evidence.
3. **Comparator and health:** matched successful trace plus downstream minute-level health metrics.

Give every worker the fixed context, verified tenant, absolute window, target selector, trace ID when known, required Keychain execution mode, and its exclusive question. Workers must not repeat context/auth checks or mapping discovery, read unrelated references, change context, duplicate another lane, mutate Dynatrace, or exceed the coordinator's limits. Give each lane a maximum of three telemetry queries and a two-minute target; require coordinator approval to exceed either. As soon as its question is answered, the worker returns the claim, exact DQL, observed values, direct link when needed, correlation strength, scan metadata, and caveats, then stops. Merge only evidence that satisfies this contract.

If a worker discovers the first incident trace ID, it must notify the coordinator immediately with the ID and observed proof. The coordinator generates and publishes the Logs & Events trace-query link before waiting for any worker to finish. Stop waiting for a lane once sufficient evidence answers the user's question; interrupt an over-running or redundant worker instead of making it the critical path. Read [references/parallel-investigation.md](references/parallel-investigation.md) whenever two or more branches can run independently.

## Raw telemetry guardrails

Every `dtctl query` must use `--fetch-timeout-seconds 60`. If it times out, narrow the window or selector instead of waiting indefinitely. Every `fetch logs` or `fetch spans` query must also:

1. Use a selective filter before sorting or aggregation.
2. Use a metric-selected short window or explicit sampling across a large requested range.
3. Return only needed fields and end with `limit 20` unless a larger bounded result is justified.
4. Use `-o json --plain`; start each investigation's first raw query with `--default-scan-limit-gbytes 5`.

Do not repeat an unchanged capped query. Strengthen its selector or sampling first, then raise the cap incrementally only when necessary. Get approval before an unsampled raw window over two hours, a weakly filtered fetch, a custom bucket, or a cap over 50 GB. Never exceed 50 GB without explicit approval.

Read [references/raw-query-controls.md](references/raw-query-controls.md) before large-range raw telemetry, sampling, scan-cap escalation, or invalid-DQL recovery. Read [references/trace-log-correlation.md](references/trace-log-correlation.md) before correlating logs and traces.

## Evidence output

Retain a proof bundle for every material claim:

- selected context and exact DQL;
- concrete observed values, IDs, and absolute timeframe;
- direct tenant-correct Dynatrace link;
- correlation strength and any permission, retention, sampling, or scan caveat.

Generate Logs and Events Advanced-mode DQL evidence links as soon as their supporting query succeeds instead of batching them at the end. Use `scripts/src/build_logs_events_graph_link.py` only for native `timeseries` DQL with an explicit interval and uncollapsed numeric arrays, and use `scripts/src/build_logs_events_link.py` for tables and categorical scalar summaries. Format linked DQL with the data source on the first line and each pipeline command on its own subsequent line; never flatten a query into one long line for a URL. Generate independent remaining links concurrently. Do not rerun successful DQL solely because a link was generated from it. Use private temporary storage outside the service repository and clean it up.

Keep graph DQL compatible with Logs and Events Classic: preserve the `timeframe`, `interval`, and numeric arrays returned by `timeseries`, and use `visualizationType=barChart` so time is always the x-axis. Do not use `scalar:true`, `summarize`, or array-reduction functions to prepare a graph link; those collapse the time dimension and belong in prose calculations or a separate table link. Prefer separate readable time-series graphs when request volume and latency/error-rate scales would obscure each other.

For a quick rundown, treat the inline three-panel timeline as the primary visualization and the same native time-series DQL in a Dynatrace bar-chart link as optional proof. Do not collapse the linked arrays or render them as a table. Read [references/query-strategy.md](references/query-strategy.md) for the reusable builder command and adaptation examples.

In the final answer, lead with human-readable findings and localize timestamps to the user's timezone while retaining the absolute UTC window. For standard broad reviews, include graph links beside the trend claims and use compact tables for endpoint or status totals. For quick rundowns, follow the fast-path answer limit and end with a focused follow-up question. For a single RID, lead with the request outcome and the exact trace/log links.

Place descriptive links beside supported claims. For standard or deep investigations, include a compact final evidence table. Read [references/evidence-links.md](references/evidence-links.md) when generating log, metric, or selective-query links and before writing the final answer.

## Out of scope

Do not create, edit, apply, delete, share, or restore dashboards, notebooks, workflows, settings, extensions, buckets, or other Dynatrace resources. State that this skill supports read-only telemetry investigation only.
