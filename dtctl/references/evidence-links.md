# Dynatrace evidence links

Use this reference to route each successful observation to the Dynatrace app that best explains it. The top-level skill contains the mandatory early exact-trace rule.

Dynatrace documents the [Distributed Tracing app](https://docs.dynatrace.com/docs/observe/application-observability/distributed-tracing/distributed-tracing-app) as the place for end-to-end trace waterfalls, spans, attributes, and correlated logs. It documents the [Synthetic app](https://docs.dynatrace.com/docs/observe/digital-experience/synthetic/synthetic-app) as the place to manage monitors and inspect reporting and executions. Synthetic discovery uses the monitor types in [Synthetic monitors in Smartscape](https://docs.dynatrace.com/docs/observe/digital-experience/synthetic/synthetic-smartscape).

## Route by evidence type

| Evidence in the answer | Direct destination | Link method |
| --- | --- | --- |
| One known `trace.id` | Distributed Tracing single-trace waterfall | `dynatrace.distributedtracing/view-trace` |
| A filtered set of requests or spans | Distributed Tracing explorer | `dynatrace.distributedtracing/view-traces` |
| Synthetic monitor identity, configuration, or current health | Synthetic monitor details | `dynatrace.synthetic/view-synthetic-monitor` |
| Synthetic failures, performance, or run history | Synthetic executions | `dynatrace.synthetic/view-synthetic-monitor-executions` |
| Bounded logs | Logs and Events Advanced-mode table | `scripts/src/build_logs_events_link.py` |
| Metric time trend requested by the user | Existing time-series bar chart with time on the x-axis | `scripts/src/build_logs_events_graph_link.py` |
| Scalar metric summary, ranking, or other DQL records | Logs and Events Advanced-mode table | `scripts/src/build_logs_events_link.py` |
| Another concrete Dynatrace resource | Its installed owning app | Discover with `dtctl get intents --app APP-ID` and verify with `dtctl describe intent APP-ID/INTENT-ID` |

Do not use a query app merely because DQL found the resource. Discovery and evidence presentation are separate: use DQL to find an exact trace or monitor, then link the trace or monitor in its owning app. If the answer cites different evidence types, provide separate links beside the claims they support.

## App-native links

Use the selected read-only context and `dtctl open intent` without `--browser`. It prints a tenant-correct AppShell URL and does not open the UI or change a Dynatrace resource.

### Exact trace

As soon as a valid trace ID is observed, create a private temporary JSON payload:

```json
{
  "trace.id": "TRACE-ID",
  "dt.timeframe": {
    "from": "WINDOW-START",
    "to": "WINDOW-END"
  }
}
```

```bash
dtctl --context "$DT_CONTEXT" open intent \
  dynatrace.distributedtracing/view-trace \
  --data-file "$PAYLOAD_FILE" \
  --plain
```

Use the returned Distributed Tracing link as the primary trace evidence. A bounded `fetch spans` query may still be used to inspect or tabulate spans, but its Logs and Events link is not a substitute for the single-trace waterfall.

For a trace set, use `dynatrace.distributedtracing/view-traces` with the installed intent schema. Supply a selective `dt.filter` and bounded `dt.timeframe`; do not fall back to an arbitrary log-query page.

### Synthetic monitor or executions

After a Smartscape query returns an exact HTTP, browser, or network monitor ID, link the monitor itself:

```json
{
  "monitorId": "MONITOR-ID",
  "dt.timeframe": {
    "from": "WINDOW-START",
    "to": "WINDOW-END"
  }
}
```

```bash
# Identity, configuration, status, or monitor-level finding
dtctl --context "$DT_CONTEXT" open intent \
  dynatrace.synthetic/view-synthetic-monitor \
  --data-file "$PAYLOAD_FILE" \
  --plain

# A claim about run history, a failure, availability, or performance
dtctl --context "$DT_CONTEXT" open intent \
  dynatrace.synthetic/view-synthetic-monitor-executions \
  --data-file "$PAYLOAD_FILE" \
  --plain
```

Use the direct Synthetic link as primary evidence. Do not link the Smartscape discovery query as though it were the monitor page. If a tenant exposes only type-specific intents, inspect the installed schema and use `view_http_monitor`, `view_browser_monitor`, or `view_network_availability_monitor` with its required property.

Delete every temporary payload after URL generation. Do not place customer data, captured headers, secrets, full log content, or sensitive selectors in an intent payload.

## DQL table and graph links

Use the environment URL from `dtctl config describe-context "$DT_CONTEXT" --plain` as the tenant source. Never guess a hostname, reuse another context's URL, or cross the production boundary.

For table evidence:

```bash
python3 scripts/src/build_logs_events_link.py \
  --environment-url "$DT_ENV_URL" \
  --dql-file "$DQL_FILE"
```

For a requested metric trend:

```bash
python3 scripts/src/build_logs_events_graph_link.py \
  --environment-url "$DT_ENV_URL" \
  --dql-file "$DQL_FILE"
```

The graph helper keeps `visualizationType=barChart`, requires a native `timeseries` query with an explicit interval, and rejects `scalar:true` and `summarize`. This preserves the time axis and prevents visualization regressions. Do not redraw telemetry locally.

### Keep DQL readable

Write the data-source command on the first line and every pipeline command on its own subsequent line. Preserve the newlines in executed commands, temporary files, and encoded links. The link builders reject inline pipeline chains.

```dql
fetch logs, from:"2026-01-01T12:00:00Z", to:"2026-01-01T12:05:00Z"
| filter log.source == "checkout-b" and env == "stg"
| fields timestamp, loglevel, trace_id, span_id, k8s.pod.name
| sort timestamp asc
| limit 20
```

For a metric trend, preserve returned arrays and dimensions:

```dql
timeseries requests=sum(dt.service.request.count), interval:15m, by:{service.name, failed}, filter:{startsWith(service.name, "[prd]") and endsWith(service.name, "]agentic-commerce-orchestrator")}, from:"2026-08-19T20:33:13Z", to:"2026-08-20T20:33:13Z", nonempty:true
| sort service.name asc, failed asc
```

Do not add comments, scan-limit settings, secrets, full log content, or explanatory prose to linked DQL. Keep absolute `from` and `to` values in the query. Create DQL files in private temporary storage outside the repository and delete them after URL generation.

## Validate without opening

- Confirm every hostname matches the environment URL for `DT_CONTEXT`.
- For an exact trace, confirm the path contains `/ui/intent/dynatrace.distributedtracing/view-trace` and the decoded fragment contains the exact `trace.id` and bounded timeframe.
- For Synthetic, confirm the path contains the chosen `/ui/intent/dynatrace.synthetic/` intent and the decoded fragment contains the exact monitor ID and bounded timeframe.
- For a DQL table or graph, confirm the path is `/ui/apps/dynatrace.classic.logs.events/ui/logs-events`, decode and compare the exact multiline DQL, and confirm `visualizationType=table` or `barChart` as intended.
- For a graph, also confirm an explicit interval, native arrays, and no `scalar:true` or `summarize` stage.
- Retain observed values as proof. A generated link makes them reproducible; the link alone does not prove the query returned data.

Do not invoke a browser on the normal path. Open a link only when the user explicitly requests UI validation or reports that it is broken. If the owning app or intent is unavailable, label the result **unlinked interim evidence** and link any independent log or metric claims in their appropriate views; do not mislabel a query-page link as the missing resource.

## Cite evidence

Place descriptive Markdown links immediately beside supported claims:

```markdown
Checkout-B returned HTTP 500 [failed trace waterfall](DIRECT-TRACE-LINK), and its pod logged a
connection refusal to Cart-B [supporting logs](DIRECT-LOG-LINK). The request originated from
[Synthetic monitor executions](DIRECT-SYNTHETIC-LINK).
```

Links are reproducible, not immutable. Telemetry can age out and access controls still apply, so always retain supporting values in the answer.
