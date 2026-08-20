# Dynatrace evidence links

Use this reference for browser-free metric graphs, record tables, trace-query links, and final-report links. The top-level skill contains the mandatory early trace-query rule.

## Proof and link contract

An investigation is complete only when material conclusions have both observed `dtctl` results and direct Dynatrace links another authenticated user can open. A trace ID, timestamp, entity ID, pod name, copied DQL, or tenant home page is context, not a substitute for a direct evidence link.

Use the environment URL from `dtctl config describe-context "$DT_CONTEXT" --plain` as the tenant source. Append only the canonical classic Logs and Events Advanced-mode route documented below; never guess a hostname, reuse another context's link, or cross the production boundary. Select a line chart for metric trends and a table for discrete records.

## Choose a human-readable visualization

- Use a **line chart** for aggregate prompts about traffic, request rate, performance, latency, or error rate over time. This includes prompts such as “traffic over the last day,” “performance in the last day,” and “latency/error rate in the last day.”
- Use a **table** for one RID, request ID, or trace ID; bounded logs or spans; exact record inspection; scalar rankings; and categorical totals.
- Give broad reviews a small number of readable series. Prefer region, a few important endpoints, status class, or latency percentiles over dozens of endpoint/status combinations.
- Preserve `timeframe`, `interval`, grouping dimensions, and metric arrays in graph DQL. Do not add `scalar:true`, `arraySum`, or `arrayMax` to the graph query. Run a companion scalar query for prose totals and rankings.
- Never make users decode JSON arrays. State totals, rates, peaks, percentiles, and localized peak times in prose, then link the graph as supporting evidence.

## Generate links without a browser

Every evidence link must open the exact raw DQL in the classic Logs and Events app with Advanced mode enabled. Do not use the `dynatrace.logs` app or `dtctl open intent` for evidence links: notebook query intents can offer to add content to an existing notebook, while trace and log-entry intents produce inconsistent destinations. Do not provide Logs-app, notebook, dashboard, distributed-trace, or single-log-entry links as fallbacks.

For table evidence:

```bash
# DT_ENV_URL is the exact environment URL returned by describe-context.
# DQL_FILE is a private temporary text file containing formatted DQL.
python3 scripts/build_logs_events_link.py \
  --environment-url "$DT_ENV_URL" \
  --dql-file "$DQL_FILE"
```

For a metric graph:

```bash
python3 scripts/build_logs_events_graph_link.py \
  --environment-url "$DT_ENV_URL" \
  --dql-file "$DQL_FILE"
```

Run the helper from the `dtctl` skill directory. It URI-encodes the DQL, Base64-encodes that value, and emits this route:

```text
TENANT-ENVIRONMENT-URL/ui/apps/dynatrace.classic.logs.events/ui/logs-events?gtf=-2h&gf=all&sortDirection=desc&visibleColumns=timestamp&visibleColumns=status&visibleColumns=content&advancedQueryMode=true&visualizationType=table&isDefaultQuery=true#BASE64-OF-URI-ENCODED-DQL
```

The graph helper uses the same path with `visualizationType=lineChart` and omits table-only visible-column parameters. Both fragments are client-side app state: they open a one-time advanced query and do not create, update, or target a notebook or other saved Dynatrace resource. Keep the absolute `from` and `to` in the DQL itself; the route's `gtf=-2h` only initializes the app and must not replace the bounded query timeframe.

## Format linked DQL for the editor

Write the data-source command on the first line and every pipeline command on its own subsequent line. Preserve these newlines in the encoded fragment even if the equivalent `dtctl query` shell command was written on one line.

```dql
fetch logs, from:"2026-01-01T12:00:00Z", to:"2026-01-01T12:05:00Z"
| filter log.source == "checkout-b" and env == "stg"
| fields timestamp, loglevel, trace_id, span_id, k8s.pod.name
| sort timestamp asc
| limit 20
```

For a regional traffic graph, retain the returned series:

```dql
timeseries requests=sum(dt.service.request.count), interval:15m, by:{service.name}, filter:{startsWith(service.name, "[prd]") and endsWith(service.name, "]agentic-commerce-orchestrator")}, from:"2026-08-19T20:33:13Z", to:"2026-08-20T20:33:13Z", nonempty:true
| fields timeframe, interval, service.name, requests
| sort service.name asc
```

Do not add comments, scan-limit settings, secrets, full log content, or explanatory text to the linked DQL. The URL should reproduce only the safe, bounded query that supports the claim.

Create DQL files in private temporary storage outside the user's repository and delete them after URL generation. Generate each evidence link when its source query succeeds; do not wait for the final reporting phase. Generate independent links concurrently.

- **Metric trends:** link the exact metric DQL, dimensions, and absolute timeframe with the line-chart helper.
- **Metric totals or rankings:** use the table helper for scalar or categorical results, normally as companion evidence to a trend graph.
- **Traces:** link a bounded `fetch spans` query. For one known trace ID, filter with `trace.id == toUid("TRACE-ID")`; never substitute the distributed-trace intent.
- **Logs:** link a bounded `fetch logs` query, including for a single record; never substitute the single-log-entry intent.
- **Other Grail records:** link the exact bounded DQL in the same Logs and Events Advanced-mode view.

## Validate without opening

- Confirm the URL hostname equals the environment URL for `DT_CONTEXT`.
- Confirm the path is exactly `/ui/apps/dynatrace.classic.logs.events/ui/logs-events`.
- Confirm `advancedQueryMode=true` and the expected visualization: `visualizationType=lineChart` for graphs or `visualizationType=table` with the expected visible columns for tables.
- Base64-decode the fragment, URI-decode the result, and compare the exact multiline DQL, absolute timeframe, and any trace ID or record selector.
- Reject the link if its path contains `/ui/intent/`, `dynatrace.logs`, `dynatrace.notebooks`, `dynatrace.distributedtracing`, or `view-log-entry`.
- Retain observed query values as proof. A generated link makes them reproducible; the link alone does not prove the query returned data.

Do not invoke a browser on the normal path. Open a link only when the user explicitly requests UI validation or reports that it is broken.

Do not place secrets, captured headers, customer data, full log content, or sensitive selectors in a URL. Prefer technical identifiers and selective telemetry fields. If the only selector is sensitive, omit it and explain the evidence limitation.

If Logs and Events is unavailable or the query is too sensitive to place in a URL, label the finding **unlinked interim evidence** instead of falling back to the Logs app, a notebook, or another app. If trace access is denied, link the log or metric queries those sources support and state that trace evidence was unavailable.

## Cite evidence

Place descriptive Markdown links immediately beside supported claims. Preserve the exact failed-trace query link already sent in commentary.

```markdown
The failed request was isolated to use1 [failure-rate graph and regional comparison](DIRECT-METRIC-GRAPH-LINK).
Checkout-B returned HTTP 500 [failed trace query](DIRECT-TRACE-QUERY-LINK), and its pod logged a
connection refusal to Cart-B [supporting logs](DIRECT-LOG-LINK).

| Source | Observed proof | Dynatrace |
|---|---|---|
| Metrics | One failed GET in use1, 03:19–03:20 UTC | [Failure-rate graph](DIRECT-METRIC-GRAPH-LINK) |
| Trace | Trace ID, HTTP 500, 333 ms | [Failed request spans](DIRECT-TRACE-QUERY-LINK) |
| Logs | Connection refused at 03:19:50 UTC | [Supporting logs](DIRECT-LOG-LINK) |
```

Links are reproducible, not immutable. Telemetry can age out and access controls still apply, so always retain supporting values in the answer.
