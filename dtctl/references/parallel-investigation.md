# Parallel investigation protocol

Use this reference whenever two or more read-only investigation branches can run independently.

## Coordinator responsibilities

The coordinator must establish once:

- fixed `DT_CONTEXT` and verified tenant URL;
- logical-service selector and service note;
- absolute timeframe and timezone interpretation;
- first metric-selected failure interval;
- shared scan, sampling, mutation, and macOS Keychain execution constraints.

Pass those resolved values to workers. Workers trust them and must not repeat context/auth preflight, mapping discovery, service-note loading, or timezone resolution. Each worker reads only `SKILL.md` and the one reference needed for its lane.

The coordinator owns the first representative incident trace query. When that query returns a valid incident trace ID, generate, validate, and publish its exact Dynatrace link immediately before waiting for parallel work.

## Worker lanes

Spawn up to three workers with distinct scopes:

1. **Trace topology:** query the exact failed trace and identify the first failed dependency, successful predecessors, and propagated status. Use the canonical `toUid` query below; do not rediscover field names or regenerate the exact trace link already owned by the coordinator.
2. **Log correlation:** determine native ID availability, then retrieve exact trace logs or bounded pod/time evidence for the suspected services. Stop after the decisive bounded cause query and its link succeed.
3. **Comparator and health:** select one matched successful request and check one downstream health metric in the failure minute. Stop when those controls distinguish an isolated failure from an outage.

```bash
dtctl --context "$DT_CONTEXT" query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter trace.id == toUid("TRACE-ID") | fields start_time, trace.id, span.id, parent_span.id, span.name, span.kind, duration, span.status_code, http.response.status_code, http.request.method, http.route, server.address, k8s.workload.name, k8s.pod.name | sort start_time asc | limit 20' --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain
```

If that exact-trace query reaches 5 GB after returning useful partial rows, narrow to the failed tail or raise once to 10 GB; do not launch exploratory field-name variants. Every query uses `--fetch-timeout-seconds 60`. A worker may execute at most three telemetry queries and should finish within two minutes. It must ask the coordinator before exceeding either bound.

If no trace ID is known but a small incident window is fixed, the coordinator may start trace discovery and bounded logical-service logs in parallel. The worker that first finds a valid incident trace ID must message the coordinator immediately rather than waiting to complete its lane.

Do not assign broad overlapping prompts. Workers must not change context or timeframe, repeat another lane's queries, escalate caps beyond the shared rules, access a browser, mutate Dynatrace, or present unsupported root cause.

Workers return as soon as their exclusive question is materially answered. They do not continue for completeness, wait for another worker, repeat evidence the coordinator already owns, or add optional corroboration. The coordinator stops waiting once the available lanes answer the user's question and interrupts an over-running or redundant lane.

## Worker prompt contract

Include:

```text
Context: sandbox (fixed; do not change)
Environment URL: verified selected production or nonproduction URL (fixed; do not change)
Tenant URL: configured URL
Absolute window: FROM to TO
Target selector: exact logical selector
Incident trace ID: value when known
Exclusive question: one lane only
Controls: read-only, first raw cap 5 GB, selective filters, limit 20, JSON/plain
Execution: use supplied Keychain mode on the first attempt; fetch timeout 60 seconds
Budget: maximum three telemetry queries; target completion within two minutes
Do not repeat coordinator preflight or mapping work; read only the lane's required reference
Return immediately on first newly discovered incident trace ID.
```

## Worker return contract

Each worker returns:

- concise claim;
- exact executed context and DQL;
- concrete observed values and identifiers;
- direct Dynatrace link generated from that evidence;
- native trace/span, trace-only, or pod/time correlation strength;
- scan and sampling metadata;
- permission, missing-data, or ambiguity caveats.

The coordinator rejects duplicate, context-mismatched, unlinked, or unsupported findings. It may retain them only as clearly labeled interim evidence.

Run repository code inspection concurrently with telemetry branches only when it helps explain propagation semantics. Telemetry remains authoritative for what happened during the incident.
