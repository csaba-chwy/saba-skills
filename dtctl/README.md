# dtctl environment setup

Configure separate read-only Dynatrace contexts for nonproduction and production. Nonproduction covers `stg`, `qat`, and `dev`; production is only for `prd`.

## Prerequisites

Install `dtctl` and export these variables from `~/.zshrc`:

- `DTCTL_NONPROD_ENVIRONMENT`
- `DTCTL_PROD_ENVIRONMENT`
- `DT_NONPROD_PLATFORM_TOKEN`
- `DT_PROD_PLATFORM_TOKEN`

Never print or commit the token values.

## Configure credentials and contexts

Run the following in zsh. It reloads the variables, stores each token under a separate macOS Keychain entry, creates read-only contexts, verifies both environments, and leaves nonproduction as the default context.

```bash
set +x
source ~/.zshrc

[[ -n "${DTCTL_NONPROD_ENVIRONMENT:-}" ]] || { print -u2 'DTCTL_NONPROD_ENVIRONMENT is not set'; exit 1; }
[[ -n "${DTCTL_PROD_ENVIRONMENT:-}" ]] || { print -u2 'DTCTL_PROD_ENVIRONMENT is not set'; exit 1; }
[[ -n "${DT_NONPROD_PLATFORM_TOKEN:-}" ]] || { print -u2 'DT_NONPROD_PLATFORM_TOKEN is not set'; exit 1; }
[[ -n "${DT_PROD_PLATFORM_TOKEN:-}" ]] || { print -u2 'DT_PROD_PLATFORM_TOKEN is not set'; exit 1; }
[[ "$DTCTL_NONPROD_ENVIRONMENT" == https://* ]] || { print -u2 'DTCTL_NONPROD_ENVIRONMENT must be an https URL'; exit 1; }
[[ "$DTCTL_PROD_ENVIRONMENT" == https://* ]] || { print -u2 'DTCTL_PROD_ENVIRONMENT must be an https URL'; exit 1; }

dtctl config set-credentials nonprod-token --token "$DT_NONPROD_PLATFORM_TOKEN" --plain
dtctl config set-credentials prod-token --token "$DT_PROD_PLATFORM_TOKEN" --plain

dtctl config set-context nonprod \
  --environment "$DTCTL_NONPROD_ENVIRONMENT" \
  --token-ref nonprod-token \
  --safety-level readonly \
  --description 'Nonproduction: stg, qat, dev' \
  --plain

dtctl config set-context prod \
  --environment "$DTCTL_PROD_ENVIRONMENT" \
  --token-ref prod-token \
  --safety-level readonly \
  --description 'Production: prd' \
  --plain

dtctl --context nonprod auth status --plain
dtctl --context prod auth status --plain
dtctl --context nonprod query 'fetch dt.entity.service | fields id | limit 1' --default-scan-limit-gbytes 1 -o json --plain
dtctl --context prod query 'fetch dt.entity.service | fields id | limit 1' --default-scan-limit-gbytes 1 -o json --plain

dtctl config use-context nonprod --plain
```

Do not delete or overwrite legacy credentials unless that cleanup is explicitly intended. Updating the named `nonprod` and `prod` contexts to their dedicated token references is sufficient.
