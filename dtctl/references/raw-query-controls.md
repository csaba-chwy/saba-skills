# Raw-query controls

Read this reference before large-range raw telemetry, sampling, scan-cap escalation, or invalid-DQL recovery.

## Required controls

Every `fetch logs` or `fetch spans` query must:

1. Use a metric-selected incident window or an explicit sampling ratio across the full requested range.
2. Filter on a selective target such as paired `log.source` and `env`, exact entity, trace ID, namespace, workload, pod, or host before sorting or aggregation.
3. Return only fields needed for the next step and end with `limit 20`; never exceed 100 without a reason.
4. Use `-o json --plain` and start the first raw query at `--default-scan-limit-gbytes 5`.
5. Use `--fetch-timeout-seconds 60`; after a timeout, narrow the window or selector rather than waiting or rerunning unchanged.

A result limit does not cap Grail scan cost.

## Scan-cap escalation

When a required query reaches its cap:

1. Confirm the target, timeframe, fields, and operation are still needed.
2. Strengthen selectors, reuse a metric-selected interval, remove unnecessary fields, or increase sampling first.
3. If still required, raise the cap by the smallest useful step: prefer 5 to 10 to 20 GB, then 10 GB steps up to 50 GB.
4. Never rerun unchanged capped DQL without changing its shape, sampling ratio, or cap.
5. Reuse a proven higher cap only for closely related queries in the same investigation; start a separate investigation at 5 GB.

Get approval before an unsampled raw window over two hours, a weakly filtered query, a custom bucket, or a scan cap over 50 GB. Never exceed 50 GB without explicit approval.

## Sample large ranges

For large requested ranges, keep the full range and sample after the metric pass:

1. Start with `--default-sampling-ratio 10` and a 5 GB cap. Increase by powers of ten before raising the cap.
2. Include `--metadata=scannedBytes,sampled,analysisTimeframe`; confirm sampling is true and the analysis timeframe matches the request.
3. Use the full-range sample to discover schemas, recurring types, and candidate dependency fields.
4. Stratify evidence with metric-selected peak and baseline intervals; cover early and late periods for multi-day ranges.
5. Use metrics for exact totals and rates. Label sampled raw rankings approximate and state the ratio.
6. Retrieve small unsampled examples only after discovering selective exact fields.

```bash
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:now()-7d
| filter k8s.workload.name == "EXACT-WORKLOAD"
| filter loglevel == "ERROR"
| fields timestamp, content, trace_id, span_id, k8s.pod.name
| sort timestamp desc
| limit 20' --fetch-timeout-seconds 60 --default-sampling-ratio 100 --default-scan-limit-gbytes 5 --metadata=scannedBytes,sampled,analysisTimeframe -o json --plain
```

Sampling can miss rare events and distort rankings. Treat samples as classification evidence, not population counts.

## Verify only invalid DQL

Execute DQL directly. Do not run `dtctl verify query` as routine preflight.

Use verification only after `dtctl query` reports a syntax, type, function, field, or semantic error. Do not verify authorization failures, scan-limit failures, transport errors, no-data results, or valid queries.

After an invalid-query error:

1. Run `dtctl verify query` on the exact failed DQL in the same context.
2. Read all locations, suggestions, and diagnostic codes. Treat `SEVERE` or `QUERY_ALWAYS_EMPTY_FILTER` as failure even if the verifier exits successfully.
3. Apply the smallest correction and execute it once with the original output, sampling, cap, and metadata controls.
