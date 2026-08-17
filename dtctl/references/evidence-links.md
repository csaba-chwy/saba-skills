# Dynatrace evidence links

Use this reference for browser-free log, metric, selective-trace, and final-report links. The top-level skill contains the mandatory early exact-trace rule.

## Proof and link contract

An investigation is complete only when material conclusions have both observed `dtctl` results and direct Dynatrace links another authenticated user can open. A trace ID, timestamp, entity ID, pod name, copied DQL, or tenant home page is context, not a substitute for a direct evidence link.

Use the environment URL from `dtctl config describe-context "$DT_CONTEXT" --plain` as the tenant source. Never hand-construct application routes, guess a hostname, reuse another context's link, or cross the production boundary.

## Generate links without a browser

`dtctl open intent` prints an AppShell URL unless `--browser` is explicitly supplied.

```bash
# Exact trace
dtctl --context "$DT_CONTEXT" open intent \
  dynatrace.distributedtracing/view-trace \
  --data trace_id="TRACE-ID" \
  --plain

# Exact DQL for logs, metrics, or a selective trace query
dtctl --context "$DT_CONTEXT" open intent \
  dynatrace.notebooks/view-query \
  --data-file "PAYLOAD.json" \
  --plain
```

Use this query payload shape:

```json
{
  "dt.query": "EXACT-DQL-WITH-ABSOLUTE-FROM-AND-TO",
  "dt.timeframe": {
    "from": "2026-01-01T12:00:00Z",
    "to": "2026-01-01T12:05:00Z"
  }
}
```

Create payloads in private temporary storage outside the user's repository and delete them after URL generation. Generate each evidence link when its source query succeeds; do not wait for the final reporting phase. Generate independent links concurrently.

- **Metrics:** link exact metric DQL, dimensions, and absolute timeframe through `dynatrace.notebooks/view-query`. Use a Data Explorer share link only when the user explicitly needs that visualization and requests browser interaction.
- **Traces:** use `dynatrace.distributedtracing/view-trace` for one known trace ID. Use `dynatrace.notebooks/view-query` for a selective multi-trace query.
- **Logs:** use `dynatrace.notebooks/view-query` for a filtered log set. Use `dynatrace.logs/view-log-entry` for one record only after `dtctl describe intent dynatrace.logs/view-log-entry` confirms the payload schema in the selected context.

Where permissions allow, use `dtctl describe intent APP-ID/INTENT-ID` to confirm the payload schema. Treat `403 Forbidden` as an intent-discovery limitation, not proof that the app or intent is absent. Known intent names documented by installed `dtctl` help may still be used; label the URL as generated and not UI-opened when discovery could not confirm it.

## Validate without opening

- Confirm the URL hostname equals the environment URL for `DT_CONTEXT`.
- Confirm the path is the intended Dynatrace AppShell intent route.
- Decode the fragment locally and compare the exact trace ID or DQL and absolute timeframe.
- Retain observed query values as proof. A generated link makes them reproducible; the link alone does not prove the query returned data.

Do not invoke a browser on the normal path. Open a link only when the user explicitly requests UI validation or reports that it is broken.

Do not place secrets, captured headers, customer data, full log content, or sensitive selectors in a URL. Prefer technical identifiers and selective telemetry fields. If the only selector is sensitive, omit it and explain the evidence limitation.

If the recipient app is unavailable, fall back to `dynatrace.notebooks/view-query` when it reproduces the claim. Otherwise label the finding **unlinked interim evidence**. If trace access is denied, link the log or metric claims those sources support and state that trace evidence was unavailable.

## Cite evidence

Place descriptive Markdown links immediately beside supported claims. Preserve the exact failed-trace link already sent in commentary.

```markdown
The failed request was isolated to use1 [failure metric and regional comparison](DIRECT-METRIC-LINK).
Checkout-B returned HTTP 500 [exact failed trace](DIRECT-TRACE-LINK), and its pod logged a
connection refusal to Cart-B [supporting logs](DIRECT-LOG-LINK).

| Source | Observed proof | Dynatrace |
|---|---|---|
| Metrics | One failed GET in use1, 03:19–03:20 UTC | [Failure minute](DIRECT-METRIC-LINK) |
| Trace | Trace ID, HTTP 500, 333 ms | [Exact failed request](DIRECT-TRACE-LINK) |
| Logs | Connection refused at 03:19:50 UTC | [Supporting logs](DIRECT-LOG-LINK) |
```

Links are reproducible, not immutable. Telemetry can age out and access controls still apply, so always retain supporting values in the answer.
