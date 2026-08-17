# Dynatrace evidence links

Use this reference for browser-free log, metric, trace-query, and final-report links. The top-level skill contains the mandatory early trace-query rule.

## Proof and link contract

An investigation is complete only when material conclusions have both observed `dtctl` results and direct Dynatrace links another authenticated user can open. A trace ID, timestamp, entity ID, pod name, copied DQL, or tenant home page is context, not a substitute for a direct evidence link.

Use the environment URL from `dtctl config describe-context "$DT_CONTEXT" --plain` as the tenant source. Append only the canonical Logs & Events route documented below; never guess a hostname, reuse another context's link, or cross the production boundary.

## Generate links without a browser

Every evidence link must open the exact raw DQL in Logs & Events. Do not use `dtctl open intent` for evidence links: notebook query intents can offer to add content to an existing notebook, while trace and log-entry intents produce inconsistent destinations. Do not provide notebook, dashboard, distributed-trace, or single-log-entry links as fallbacks.

```bash
# DT_ENV_URL is the exact environment URL returned by describe-context.
# PAYLOAD_FILE is a private temporary JSON file using the shape below.
COMPACT_PAYLOAD=$(jq -c . "$PAYLOAD_FILE")
ENCODED_PAYLOAD=$(jq -rn --arg payload "$COMPACT_PAYLOAD" '$payload | @uri')
printf '%s/ui/apps/dynatrace.logs/#%s\n' "${DT_ENV_URL%/}" "$ENCODED_PAYLOAD"
```

Use this query payload shape:

```json
{
  "version": 2,
  "dt.query": "EXACT-DQL-WITH-ABSOLUTE-FROM-AND-TO",
  "dt.timeframe": {
    "from": "2026-01-01T12:00:00Z",
    "to": "2026-01-01T12:05:00Z"
  },
  "showDqlEditor": true
}
```

The resulting URL must have the form `TENANT-ENVIRONMENT-URL/ui/apps/dynatrace.logs/#PERCENT-ENCODED-JSON`. The fragment is client-side app state: it opens a one-time query view and does not create, update, or target a notebook or other saved Dynatrace resource.

Create payloads in private temporary storage outside the user's repository and delete them after URL generation. Generate each evidence link when its source query succeeds; do not wait for the final reporting phase. Generate independent links concurrently.

- **Metrics:** link the exact metric DQL, dimensions, and absolute timeframe in Logs & Events.
- **Traces:** link a bounded `fetch spans` query. For one known trace ID, filter with `trace.id == toUid("TRACE-ID")`; never substitute the distributed-trace intent.
- **Logs:** link a bounded `fetch logs` query, including for a single record; never substitute the single-log-entry intent.
- **Other Grail records:** link the exact bounded DQL in the same Logs & Events view.

## Validate without opening

- Confirm the URL hostname equals the environment URL for `DT_CONTEXT`.
- Confirm the path is exactly `/ui/apps/dynatrace.logs/` and the query payload is in the URL fragment.
- Decode the fragment locally and compare the exact DQL, absolute timeframe, and any trace ID or record selector.
- Reject the link if its path contains `/ui/intent/`, `dynatrace.notebooks`, `dynatrace.distributedtracing`, or `view-log-entry`.
- Retain observed query values as proof. A generated link makes them reproducible; the link alone does not prove the query returned data.

Do not invoke a browser on the normal path. Open a link only when the user explicitly requests UI validation or reports that it is broken.

Do not place secrets, captured headers, customer data, full log content, or sensitive selectors in a URL. Prefer technical identifiers and selective telemetry fields. If the only selector is sensitive, omit it and explain the evidence limitation.

If Logs & Events is unavailable or the query is too sensitive to place in a URL, label the finding **unlinked interim evidence** instead of falling back to a notebook or another app. If trace access is denied, link the log or metric queries those sources support and state that trace evidence was unavailable.

## Cite evidence

Place descriptive Markdown links immediately beside supported claims. Preserve the exact failed-trace query link already sent in commentary.

```markdown
The failed request was isolated to use1 [failure metric and regional comparison](DIRECT-METRIC-LINK).
Checkout-B returned HTTP 500 [failed trace query](DIRECT-TRACE-QUERY-LINK), and its pod logged a
connection refusal to Cart-B [supporting logs](DIRECT-LOG-LINK).

| Source | Observed proof | Dynatrace |
|---|---|---|
| Metrics | One failed GET in use1, 03:19–03:20 UTC | [Failure minute](DIRECT-METRIC-LINK) |
| Trace | Trace ID, HTTP 500, 333 ms | [Failed request spans](DIRECT-TRACE-QUERY-LINK) |
| Logs | Connection refused at 03:19:50 UTC | [Supporting logs](DIRECT-LOG-LINK) |
```

Links are reproducible, not immutable. Telemetry can age out and access controls still apply, so always retain supporting values in the answer.
