# Trace and log correlation

Read this reference before assigning logs to a trace or span.

## Determine the mapping mode

After selecting a representative span:

1. Sample logs from its exact pod and smallest useful time window without `content`; inspect `trace_id` and `span_id`.
2. If both match the selected `trace.id` and `span.id`, use native span-level mapping.
3. If only `trace_id` matches, use native trace-level mapping but do not assign the log to one span.
4. If neither is available, fetch logs by exact pod and the span interval plus a small skew margin. Label this pod/time supporting evidence. Report ambiguity when multiple spans overlap.

Reuse a confirmed native mapping within the investigation. Re-probe after deployments, mixed enrichment, or when moving to another service.

```bash
# Probe log-side IDs
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:"WINDOW-START", to:"WINDOW-END" | filter k8s.pod.name == "SPAN-POD" | fields timestamp, trace_id, span_id, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain

# Exact trace spans
dtctl --context "$DT_CONTEXT" query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter trace.id == toUid("TRACE-ID") | fields start_time, trace.id, span.id, parent_span.id, span.name, duration, span.status_code, dt.entity.service | sort start_time asc | limit 20' --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain

# Exact trace logs when native IDs exist
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:"WINDOW-START", to:"WINDOW-END" | filter trace_id == "TRACE-ID" | fields timestamp, loglevel, trace_id, span_id, dt.entity.service, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain

# Pod/time fallback
dtctl --context "$DT_CONTEXT" query 'fetch logs, from:"SPAN-START-MINUS-SKEW", to:"SPAN-END-PLUS-SKEW" | filter k8s.pod.name == "SPAN-POD" | fields timestamp, loglevel, k8s.workload.name, k8s.pod.name | sort timestamp asc | limit 20' --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain
```

Log `trace_id` is a string; span `trace.id` is a UID. Confirm a log value is 32 hexadecimal characters before using `toUid`. Shorter request or transaction identifiers are application-local correlation keys, not trace IDs.

Spans use `start_time`; logs use `timestamp`. Use time to order exact matches or as an explicitly labeled fallback. Avoid server-side joins unless separate bounded pivots cannot answer the question.

Captured HTTP headers use `http.request.header.<lowercase-name>` and can be arrays. For X-Request-ID, query the backticked `http.request.header.x-request-id` field. Treat captured values as sensitive and omit them from summaries unless required.

```bash
dtctl --context "$DT_CONTEXT" query 'fetch spans, from:"WINDOW-START", to:"WINDOW-END" | filter dt.entity.service == "SERVICE-xxx" | filter request.is_root_span == true | filter isNotNull(`http.request.header.x-request-id`) | fields start_time, trace.id, span.id, span.name, `http.request.header.x-request-id`, http.request.method, http.route, k8s.pod.name | sort start_time desc | limit 20' --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain
```

If spans return `NOT_AUTHORIZED_FOR_TABLE`, report the permission boundary. Continue with log-side correlation only when it answers part of the question, and do not describe it as verified span evidence.

If no structured or message-level IDs exist, continue with exact workload, pod, and timestamp filters. State that native log-to-trace correlation was unavailable.
