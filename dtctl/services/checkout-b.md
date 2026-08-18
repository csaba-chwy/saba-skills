# `checkout-b`

- Logs are stored in the Grail bucket `cart_checkout_logs`; this was verified for `dev`, `qat`, `stg`, and `prd` on 2026-08-18. Add `bucket:"cart_checkout_logs"` to Checkout B log fetches.
- Log enrichment varies by environment and record type. Sampled records ranged from no service or correlation fields to records with `dt.entity.service` and short `trace_id` values but no `span_id`.
- Observed enriched `trace_id` values were 5–10 characters, so treat them as application-local keys rather than trace UIDs. Use exact workload and pod/time evidence unless current records prove a native 32-hex trace ID.
