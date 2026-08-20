---
name: dtctl
description: Investigate Dynatrace services with dtctl using the correct nonprod or prod context, metric-first failure discovery, safe bounded log and trace queries, early trace-query links, and parallel evidence collection. Use for error analysis, trace-to-log correlation, deployment symptoms, Kubernetes workload logs, service latency, and service-specific observability investigations over short or long time ranges.
---

# Dynatrace investigation with dtctl

Use this skill for read-only Grail investigations. Never mutate Dynatrace resources. Treat `NOT_AUTHORIZED_FOR_TABLE` as a permission boundary; do not work around it or switch tools implicitly.

## Non-negotiable contract

- Select `DTCTL_PROD_ENVIRONMENT` only for `[prd]`; select `DTCTL_NONPROD_ENVIRONMENT` for `[stg]`, `[qat]`, and `[dev]`. If the environment is not explicit, ask. Never cross the production boundary as a fallback.
- Authenticate the selected environment with browser-based OAuth into the `sandbox` context. Do not use platform-token environment variables or `dtctl config set-credentials`.
- Always create or refresh the `sandbox` context with `--safety-level readonly`. This is mandatory for production and must not be relaxed for nonproduction.
- Pass `--context "$DT_CONTEXT"` on every `dtctl` command. Confirm the context URL and auth before querying.
- Use the context environment URL as the only tenant source. Never guess or reuse a hostname from another context.
- Start with request metrics, then narrow raw logs or spans to a selective target and a metric-selected or explicitly bounded window.
- Back every material conclusion with observed values, the exact context and DQL, and a direct Dynatrace link.
- Do not use Chrome or another browser on the normal path. Provide every evidence link as a raw, multiline DQL query in the classic Logs and Events app with Advanced mode enabled; never route evidence through the Logs app, notebooks, dashboards, the distributed-trace view, or the single-log-entry view.
- Keep secrets, customer data, full log content, and sensitive captured headers out of URLs and summaries.

## Start safely

Normalize the target into its environment tag, environment value, and telemetry stem. Read [mappings.md](mappings.md), then read only the linked file under `services/` for the requested logical service.

```bash
case "$SERVICE_NAME" in
  "[prd]"*) DT_ENVIRONMENT="$DTCTL_PROD_ENVIRONMENT" ;;
  "[stg]"*|"[qat]"*|"[dev]"*) DT_ENVIRONMENT="$DTCTL_NONPROD_ENVIRONMENT" ;;
  *) print -u2 'Cannot determine Dynatrace context from service name'; exit 1 ;;
esac
DT_CONTEXT=sandbox
[[ "$DT_ENVIRONMENT" == https://* ]] || { print -u2 'Selected Dynatrace environment is not configured as an https URL'; exit 1; }
dtctl auth login \
  --context "$DT_CONTEXT" \
  --environment "$DT_ENVIRONMENT" \
  --safety-level readonly
dtctl config describe-context "$DT_CONTEXT" --plain
dtctl --context "$DT_CONTEXT" auth status --plain
```

Confirm that the environment reported by `describe-context` exactly matches `DT_ENVIRONMENT` before querying. The `sandbox` context points to one environment at a time, so never reuse it across a production boundary without running the matching login command again and rechecking the URL and safety level. If OAuth or a keychain-backed credential is unavailable only inside the sandbox, retry the same command once with normal browser and Keychain access rather than changing tools or authentication. Once that retry proves the context uses macOS Keychain credentials, run every later `dtctl` command in this investigation with normal Keychain access on its first attempt. Do not incur a sandbox failure and approval wait for every query.

## Apply the shared service baseline

Treat each file under `services/` as a small set of service-specific overrides to this baseline, not a complete investigation recipe:

- Re-probe current telemetry before relying on a dated enrichment observation. Use the logical selectors first. Resolve an exact tagged service or workload only when a logical selector is absent or ambiguous, and rank duplicate entities by current request traffic.
- Inspect the dimensions actually returned by `dt.service.request.count`. Common dimensions include `failed`, `endpoint.name`, HTTP method and status, workload, and version, but partially enriched operations can omit some of them.
- Probe log service, entity, trace, and span fields before choosing a correlation mode. A native trace ID is 32 hexadecimal characters and a native span ID is 16 hexadecimal characters; shorter values are application-local keys. Use exact native IDs only when the sampled values validate them, otherwise use exact workload, pod, and a tight time window as supporting evidence.
- Expect spans to expose pod and workload identity plus server, client, or internal activity. Root spans can expose routes and X-Request-ID, but neither is guaranteed; treat captured request headers as sensitive.
- When a service note names a Grail log bucket, add `bucket:"BUCKET-NAME"` to every `fetch logs` query for that service. Keep the paired `log.source` and `env` filter as the logical selector even when the bucket narrows the scan.

## Investigation workflow

1. Resolve the target, context, absolute requested timeframe, and timezone interpretation once.
2. Use `dt.service.request.count` to locate traffic, failures, regions, and the smallest useful incident window. Run independent metric timeline and catalog queries concurrently.
3. Query the root span or other most selective source needed to identify a representative failed trace.
4. **Immediately publish the trace-query link** using the rule below.
5. Run trace topology, log correlation, and comparator/downstream-health work in parallel when those branches are independent.
6. Synthesize only returned evidence, distinguish exact native correlation from pod/time support, and include linked proof beside every material claim.

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

Use subagents freely when independent read-only branches exist and execution slots are available. The coordinator owns the context, absolute timeframe, selector, initial metric pass, early user-facing trace link, and final synthesis.

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

Generate Logs and Events Advanced-mode DQL evidence links as soon as their supporting query succeeds instead of batching them at the end. Format linked DQL with the data source on the first line and each pipeline command on its own subsequent line; never flatten a query into one long line for a URL. Generate independent remaining links concurrently. Do not rerun successful DQL solely because a link was generated from it. Use private temporary storage outside the service repository and clean it up.

Place descriptive links beside supported claims and include a compact final evidence table. Read [references/evidence-links.md](references/evidence-links.md) when generating log, metric, or selective-query links and before writing the final answer.

## Out of scope

Do not create, edit, apply, delete, share, or restore dashboards, notebooks, workflows, settings, extensions, buckets, or other Dynatrace resources. State that this skill supports read-only telemetry investigation only.
