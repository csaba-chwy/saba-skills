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
  'fetch logs, from:now()-15m | fields timestamp, loglevel | sort timestamp desc | limit 1' \
  --fetch-timeout-seconds 60 --default-scan-limit-gbytes 5 -o json --plain
```

The verification queries intentionally return only minimal, non-sensitive fields. A successful empty result still proves authorization; an authorization error does not. Do not print, export, or commit stored OAuth credentials.
