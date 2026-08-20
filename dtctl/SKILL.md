---
name: dtctl
description: Investigate Dynatrace services with dtctl through read-only production and nonproduction contexts. Use for quick service rundowns, request/error/latency checks, error diagnosis, trace-to-log correlation, deployment symptoms, Kubernetes workload logs, and service-specific observability investigations.
---

# Dynatrace investigation with dtctl

Use read-only Grail telemetry and return tenant-correct Dynatrace links. Treat `NOT_AUTHORIZED_FOR_TABLE` as the access boundary.

## Route the environment

| Target | Context | Environment URL |
| --- | --- | --- |
| `prd` | `prod` | `DTCTL_PROD_ENVIRONMENT` |
| `stg`, `qat`, `dev` | `nonprod` | `DTCTL_NONPROD_ENVIRONMENT` |

Keep both contexts at safety level `readonly`. Pass `--context` to every query and use the selected context URL for links.

## Quick rundown

Use this path for “rundown,” “quick health check,” “at a glance,” and similar summary requests. It intentionally returns four scalar metrics and one reproducible table link.

From this skill directory, run:

```bash
python3 scripts/src/run_service_rundown.py \
  --environment prd \
  --service sf-item \
  --lookback 1d
```

The script deterministically:

1. Resolves an absolute UTC window.
2. Verifies the matching context URL, `readonly` safety level, and reusable OAuth session.
3. Runs one bounded query for requests, failed requests, error rate, and p95 latency.
4. Prints ready-to-send Markdown with one exact Dynatrace Logs and Events table link.

Run the command with normal network and macOS Keychain access when the execution sandbox requires it. Return its stdout directly and stop. Reserve interpretation, extra queries, logs, spans, entity lookup, local charts, and browser/UI work for explicitly requested drilldowns.

If authentication is unavailable, report the exact login command printed by the script and stop. The user can run that command manually; rerun the rundown after authentication succeeds.

## Standard investigation

For debugging, root cause, exact records, logs, traces, breakdowns, or trend analysis:

1. Fix the environment, service, absolute window, and user timezone.
2. Read [mappings.md](mappings.md), the linked service note, and [references/query-strategy.md](references/query-strategy.md).
3. Start with `dt.service.request.count` to locate traffic, failures, and a narrow incident window.
4. Query only the logs or spans needed to answer the question. Read [references/raw-query-controls.md](references/raw-query-controls.md) before raw queries and [references/trace-log-correlation.md](references/trace-log-correlation.md) before correlation.
5. Generate direct evidence links with the bundled Python link builders. Read [references/evidence-links.md](references/evidence-links.md) for the required link shape.
6. Return observed values, the exact UTC window, concise conclusions, and links beside the claims they support.

When a failed request yields a valid 32-character `trace.id`, immediately link this bounded query before continuing:

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

## Link builders

Use `scripts/src/build_logs_events_link.py` for scalar summaries and record tables. Use `scripts/src/build_logs_events_graph_link.py` only when the user explicitly asks for a time trend. Both encode multiline DQL into the classic Logs and Events Advanced-mode route without opening a browser or creating Dynatrace resources.

Keep the entire workflow read-only; dashboards, notebooks, workflows, settings, extensions, buckets, and other Dynatrace resources stay unchanged.
