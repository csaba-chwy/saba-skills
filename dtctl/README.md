# dtctl environment setup

Authenticate to the selected Dynatrace environment with browser-based OAuth. Nonproduction covers `stg`, `qat`, and `dev`; production is only for `prd`. The shared `sandbox` context points to one environment at a time and is always read-only.

## Prerequisites

Install `dtctl` and export these variables from `~/.zshrc`:

- `DTCTL_NONPROD_ENVIRONMENT`
- `DTCTL_PROD_ENVIRONMENT`

These variables contain environment URLs, not platform tokens. Platform-token environment variables are no longer used.

## Log in

Run the command for the target environment. Each command opens the Dynatrace OAuth browser flow, stores the resulting OAuth credentials securely, and creates or refreshes the `sandbox` context with read-only safety.

For `stg`, `qat`, or `dev`:

```bash
[[ -n "${DTCTL_NONPROD_ENVIRONMENT:-}" ]] || { print -u2 'DTCTL_NONPROD_ENVIRONMENT is not set'; exit 1; }
[[ "$DTCTL_NONPROD_ENVIRONMENT" == https://* ]] || { print -u2 'DTCTL_NONPROD_ENVIRONMENT must be an https URL'; exit 1; }

dtctl auth login \
  --context sandbox \
  --environment "$DTCTL_NONPROD_ENVIRONMENT" \
  --safety-level readonly
```

For `prd`:

```bash
[[ -n "${DTCTL_PROD_ENVIRONMENT:-}" ]] || { print -u2 'DTCTL_PROD_ENVIRONMENT is not set'; exit 1; }
[[ "$DTCTL_PROD_ENVIRONMENT" == https://* ]] || { print -u2 'DTCTL_PROD_ENVIRONMENT must be an https URL'; exit 1; }

dtctl auth login \
  --context sandbox \
  --environment "$DTCTL_PROD_ENVIRONMENT" \
  --safety-level readonly
```

Production must always use `--safety-level readonly`. Do not substitute `readwrite-mine`, `readwrite-all`, or `dangerously-unrestricted`. Because both commands update the same context, running one replaces the `sandbox` context's selected environment; never use its prior tenant URL as proof of the current target.

## Verify the selected environment

Confirm the context URL, OAuth status, read-only safety level, and access to each telemetry type:

```bash
dtctl config describe-context sandbox --plain
dtctl --context sandbox auth status --plain

dtctl --context sandbox query \
  'timeseries requests=sum(dt.service.request.count, scalar:true), from:-15m | fields requests | limit 1' \
  --fetch-timeout-seconds 60 -o json --plain

dtctl --context sandbox query \
  'fetch spans, from:now()-15m | fields start_time, trace.id | sort start_time desc | limit 1' \
  --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain

dtctl --context sandbox query \
  'fetch logs, from:now()-15m | fields timestamp, loglevel | sort timestamp desc | limit 1' \
  --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain
```

The verification queries intentionally return only minimal, non-sensitive fields. A successful empty result still proves authorization; an authorization error does not. Do not print, export, or commit stored OAuth credentials.
