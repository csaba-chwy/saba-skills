# `checkout-a`

- Logs are stored in the Grail bucket `cart_checkout_logs`; this was verified for `dev`, `qat`, `stg`, and `prd` on 2026-08-18. Add `bucket:"cart_checkout_logs"` to Checkout A log fetches.
- Workload logs have mixed enrichment. Some records carry `dt.entity.service` and `trace_id` but no `span_id`; other records carry none of them, and `service.name` is absent.
- Observed log `trace_id` values were 5–15 characters, not 32-character trace UIDs. Treat them as application-local correlation keys; do not pass them to `toUid` or claim native trace correlation.
