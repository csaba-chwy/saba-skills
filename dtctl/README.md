# dtctl environment setup

Authenticate to Dynatrace with browser-based OAuth. Use the `nonprod` context for `stg`, `qat`, and `dev`, and use the `prod` context only for `prd`. Both contexts are always read-only.

## Prerequisites

Install `dtctl` and export these variables from `~/.zshrc`:

- `DTCTL_NONPROD_ENVIRONMENT`
- `DTCTL_PROD_ENVIRONMENT`

These variables contain environment URLs, not platform tokens. Platform-token environment variables are no longer used.

## Reuse an existing login

Select the context for the target environment and inspect it before starting a browser login:

```bash
DT_CONTEXT=nonprod # Use prod only for prd.
dtctl config describe-context "$DT_CONTEXT" --plain
dtctl --context "$DT_CONTEXT" auth status --plain
```

Reuse the context without logging in when its environment URL matches the corresponding configured environment, its safety level is `readonly`, and its browser-based OAuth session has either an unexpired access token or a refresh token. `dtctl` can automatically refresh an expired access token when a refresh token remains, so do not run `dtctl auth login` in that case.

Run the matching login command only when the context is absent or mismatched, or when no usable OAuth access or refresh token remains. The command opens the Dynatrace OAuth browser flow, stores the resulting credentials securely, and creates, repairs, or re-authenticates the context with read-only safety.

For `stg`, `qat`, or `dev`:

```bash
[[ -n "${DTCTL_NONPROD_ENVIRONMENT:-}" ]] || { print -u2 'DTCTL_NONPROD_ENVIRONMENT is not set'; exit 1; }
[[ "$DTCTL_NONPROD_ENVIRONMENT" == https://* ]] || { print -u2 'DTCTL_NONPROD_ENVIRONMENT must be an https URL'; exit 1; }

dtctl auth login \
  --context nonprod \
  --environment "$DTCTL_NONPROD_ENVIRONMENT" \
  --safety-level readonly
```

For `prd`:

```bash
[[ -n "${DTCTL_PROD_ENVIRONMENT:-}" ]] || { print -u2 'DTCTL_PROD_ENVIRONMENT is not set'; exit 1; }
[[ "$DTCTL_PROD_ENVIRONMENT" == https://* ]] || { print -u2 'DTCTL_PROD_ENVIRONMENT must be an https URL'; exit 1; }

dtctl auth login \
  --context prod \
  --environment "$DTCTL_PROD_ENVIRONMENT" \
  --safety-level readonly
```

Production must always use `--safety-level readonly`. Do not substitute `readwrite-mine`, `readwrite-all`, or `dangerously-unrestricted`. Keep each context bound to its matching environment URL; never configure `prod` with `DTCTL_NONPROD_ENVIRONMENT` or `nonprod` with `DTCTL_PROD_ENVIRONMENT`.

## Verify the selected environment

Select the context that matches the target, then confirm its URL, OAuth status, read-only safety level, and access to each telemetry type:

```bash
DT_CONTEXT=nonprod # Use prod only for prd.

dtctl config describe-context "$DT_CONTEXT" --plain
dtctl --context "$DT_CONTEXT" auth status --plain

dtctl --context "$DT_CONTEXT" query \
  'timeseries requests=sum(dt.service.request.count, scalar:true), from:-15m | fields requests | limit 1' \
  --fetch-timeout-seconds 60 -o json --plain

dtctl --context "$DT_CONTEXT" query \
  'fetch spans, from:now()-15m | fields start_time, trace.id | sort start_time desc | limit 1' \
  --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain

dtctl --context "$DT_CONTEXT" query \
  'fetch logs, from:now()-15m
| fields timestamp, loglevel
| sort timestamp desc
| limit 1' \
  --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain
```

The verification queries intentionally return only minimal, non-sensitive fields. A successful empty result still proves authorization; an authorization error does not. Do not print, export, or commit stored OAuth credentials.

## Quick service error summary

Dynatrace's native per-service error UI is **Services > Failures**. It complements **Problems**: Problems explains detected incidents and their impact chain, while Failure Analysis supports exploratory filtering by service, endpoint, failure type, and timeframe, with failed traces, contextual logs, downstream calls, and comparison mode. See the official [Failure Analysis documentation](https://docs.dynatrace.com/docs/observe/application-observability/services/failure-analysis).

Run the repository's metric-first summary before scanning raw logs or spans:

```bash
cd dtctl
python3 scripts/src/run_service_error_summary.py \
  --environment prd \
  --service sf-item \
  --lookback 1d
```

The script reports total and per-deployment request failures, ranks the top endpoint/HTTP-status groups, and links each active service entity directly to native Failure Analysis for the exact absolute timeframe. On the normal path it uses one metric query when there are no failures and two when a ranking is needed. If the tagged `service.name` selector is empty, it performs a capped 15-minute workload-span lookup and retries by discovered service entity ID, so null `service.name` enrichment does not hide an active service. Use `--top 10` to expand the default five groups.

## Quick Davis problem summary

Resolve the logical service to entities observed in the requested window, then
query only matching Davis problems:

```bash
cd dtctl
python3 scripts/src/run_service_problem_summary.py \
  --environment prd \
  --service sf-item \
  --lookback 1d
```

The runner performs one metric entity-resolution query and one bounded problem
query. Use `--status active` for current problems. When request metrics cannot
resolve a service entity, it skips the problem query rather than falling back to
a tenant-wide scan.

## Change regression check

Compare equal service-metric windows around a known deployment or change:

```bash
cd dtctl
python3 scripts/src/run_service_regression.py \
  --environment prd \
  --service sf-item \
  --change-time 2026-08-20T14:30:00Z
```

The runner uses one combined DQL query for request volume, failed requests,
error rate, and p95 latency. It prints a threshold-based result and stops cleanly
when there is no regression or insufficient data. Window, guard, percentile, and
threshold values are configurable through CLI flags.

The DQL authoring and Davis problem guidance is selectively adapted from
[Dynatrace for AI](https://github.com/Dynatrace/dynatrace-for-ai) at pinned
upstream commit `ec2fb22d95167539dda7811b4347543431dce824` under Apache-2.0.
Local tenant observations, read-only controls, query budgets, and direct evidence
links remain authoritative.
