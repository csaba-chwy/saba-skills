---
name: dtctl
description: Investigate Dynatrace logs with safe, bounded DQL queries using the dtctl CLI. Use for log errors, deployment symptoms, Kubernetes workload logs, and service-specific log investigation.
---

# Dynatrace log investigation with dtctl

Use this skill only for **read-only log investigation**. The configured platform token can query logs but cannot query traces; it is not intended for dashboard or other resource management.

## Start safely

```bash
dtctl auth status --plain
dtctl config current-context
```

Confirm access by running a narrow log query. Do not use `dtctl auth whoami`; it requires an OAuth/JWT identity scope that a platform token may not have.

```bash
dtctl query "fetch logs, from:now()-15m | filter dt.entity.service == \"SERVICE-xxx\" | fields timestamp, loglevel, content | sort timestamp desc | limit 20" --default-scan-limit-gbytes 5 -o json --plain
```

## Required query controls

Every `fetch logs` query must:

1. Use an explicit, small time range—start with `now()-15m`.
2. Filter on a selective target such as `dt.entity.service`, `k8s.namespace.name`, `k8s.workload.name`, `host.name`, or a known deployment attribute before sorting or aggregation.
3. Return only fields needed for the next step and end with `limit 20` (never over 100 without a reason).
4. Use `--default-scan-limit-gbytes 5` and `-o json --plain`.

A result limit does not limit Grail scan cost. For a window over two hours, a weakly filtered search, a custom bucket, or a scan cap over 20 GB, explain the cost and get the user's approval first. If the scan limit is hit, narrow the time range or filter—do not raise it without approval.

Validate unfamiliar DQL before executing it:

```bash
dtctl verify query "fetch logs, from:now()-15m | filter dt.entity.service == \"SERVICE-xxx\" | limit 20" --plain
```

## Useful patterns

```bash
# Recent errors for one service
dtctl query "fetch logs, from:now()-15m | filter dt.entity.service == \"SERVICE-xxx\" | filter loglevel == \"ERROR\" | fields timestamp, content, k8s.pod.name | sort timestamp desc | limit 20" --default-scan-limit-gbytes 5 -o json --plain

# A Kubernetes workload during a specific incident window
dtctl query "fetch logs, from:now()-30m | filter k8s.namespace.name == \"namespace\" | filter k8s.workload.name == \"workload\" | fields timestamp, loglevel, content, k8s.pod.name | sort timestamp desc | limit 20" --default-scan-limit-gbytes 5 -o json --plain

# Error count trend for a known service
dtctl query "fetch logs, from:now()-1h | filter dt.entity.service == \"SERVICE-xxx\" | filter loglevel == \"ERROR\" | makeTimeseries errors=count(), interval:5m" --default-scan-limit-gbytes 5 -o json --plain
```

Use a known entity ID or exact workload/namespace; do not begin with a tenant-wide text search. Treat log content as potentially sensitive: include only necessary fields in commands and summaries.

## Out of scope

Do not query `spans` or offer trace links: this token is not authorized for the spans table. Do not create, edit, apply, delete, share, or restore dashboards, notebooks, workflows, settings, extensions, buckets, or other Dynatrace resources. If a request needs one of those operations, state that the current token does not support it.
