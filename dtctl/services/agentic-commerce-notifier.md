# `agentic-commerce-notifier`

- Select logs across regions with `log.source == "agentic-commerce-notifier"` plus the requested `env`. A staging probe on 2026-08-13 returned only the expected `use1` and `use2` workloads; keep the workload in the first grouped result and fall back to exact workloads if that changes.
- Validated notifier logs had null `dt.entity.service`, `dt.entity.service.name`, and `service.name`; inspect correlation fields before choosing a pivot.
- Query spans by the entity ID resolved for the selected context. Queue-processing spans can expose `start_time`, `trace.id`, `span.id`, workload, and pod fields.
- If notifier-local logs lack native trace and span IDs, map one selected span to logs using its exact pod and smallest useful time window. Label this as supporting evidence, not an exact ID join.
- Re-probe enrichment in each target environment; do not assume behavior observed in one environment applies to another.

## Agentic event and webhook metrics

- Use the OpenTelemetry counter `agentic.notifier.consumer` for consumer-attempt volume. No separate received and processed counters were discovered: split this counter by `haserror` to distinguish successful and failed processing attempts, and do not call the unfiltered total successfully processed events.
- Group consumer activity by `eventtype`, `sourcetype`, and `businesschannel`. Values such as `RETURN_PROCESSED` and `RETURN_FAILED` are upstream business event types, not the notifier's processing result; use `haserror` for the latter.
- Use `sent_notification`, `vendor`, `orchestratorsessionfound`, `skiporchestratorsessioncheck`, `isduplicateevent`, and `isvendorpublishskippedbyfeaturetoggle` to explain why a consumed event did or did not proceed to vendor notification. Retain `env`, `region`, and `service.name` when comparing deployments.
- Use `agentic.notifier.vendor` for vendor/webhook publication volume and group it by `vendor`, `eventtype`, `haserror`, and `sent_notification`. Prefer this counter over `consumer` when the question is specifically about sent or failed webhooks.
- Probe dimension values before filtering. Recent production records populated the outcome and routing tags, while older nonproduction series contained nulls for several of them; Boolean-like tags may also be strings in one context and Booleans in another.

```bash
# Consumed events and notifier processing outcome.
dtctl --context "$DT_CONTEXT" query 'timeseries events=sum(agentic.notifier.consumer), interval:15m, by:{eventtype, sourcetype, haserror, sent_notification, vendor}, filter:{startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]agentic-commerce-notifier")}, from:-24h | fieldsAdd events_total=arraySum(events) | fields eventtype, sourcetype, haserror, sent_notification, vendor, events_total | sort events_total desc | limit 20' -o json --plain

# Vendor/webhook publication outcome.
dtctl --context "$DT_CONTEXT" query 'timeseries webhooks=sum(agentic.notifier.vendor), interval:15m, by:{eventtype, vendor, haserror, sent_notification}, filter:{startsWith(service.name, "[ENVIRONMENT]") and endsWith(service.name, "]agentic-commerce-notifier")}, from:-24h | fieldsAdd webhooks_total=arraySum(webhooks) | fields eventtype, vendor, haserror, sent_notification, webhooks_total | sort webhooks_total desc | limit 20' -o json --plain
```
