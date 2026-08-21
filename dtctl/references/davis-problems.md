# Davis problem investigation

Read this reference after the service problem summary returns a concrete problem
that requires deeper incident or impact analysis.

This workflow adapts Dynatrace's
[`dt-obs-problems`](https://github.com/Dynatrace/dynatrace-for-ai/tree/main/skills/dt-obs-problems)
skill at commit `ec2fb22d95167539dda7811b4347543431dce824` under Apache-2.0.

## Role of each view

- Service Failure Analysis explores failed requests by entity, endpoint, status,
  trace, contextual log, outgoing call, or database failure.
- Davis Problems groups detected symptoms, supplies impact and affected
  entities, and may identify a root-cause entity.
- Logs and traces validate a specific hypothesis after a problem or failure
  window has narrowed the search.

Do not treat the absence of a Davis problem as proof that no request failed.
Conversely, do not replace Davis's root-cause claim with a log hypothesis unless
the telemetry supports the change.

## Stable query shape

The bundled problem runner resolves exact service entities from request metrics,
then runs one bounded `dt.davis.problems` query. It filters duplicate problem
records against the tenant-populated `affected_entity_ids` and
`root_cause_entity_id` fields, then deduplicates on `display_id`. Generic
Dynatrace examples commonly use `dt.smartscape.service`, but that field was null
across the validated nonproduction problem population; do not substitute it
without proving that the target tenant populates it.

Important fields:

- `display_id`: human-readable problem identifier.
- `event.status`: `ACTIVE` or `CLOSED`.
- `event.category`: commonly `AVAILABILITY`, `ERROR`, `SLOWDOWN`,
  `RESOURCE_CONTENTION`, `CUSTOM_ALERT`, or another configured category.
- `event.start` and `event.end`: authoritative problem window.
- `dt.davis.affected_users_count`: user-impact estimate when available.
- `affected_entity_ids`: exact affected entity IDs and blast-radius input.
- `root_cause_entity_id` and `root_cause_entity_name`: Davis root-cause result
  when available.

## Bounded drill-down

1. Reuse the exact problem timeframe and affected service or workload.
2. If the user asks what failed, open native Service Failure Analysis first.
3. If the user asks why, retrieve one representative failed trace and publish
   its direct trace link before further analysis.
4. Query logs only for the exact trace or bounded pod/time context.
5. Stop when the evidence confirms or contradicts the root-cause hypothesis.

For recurring-problem questions, query the requested historical window, group by
the confirmed root-cause entity and category, and return counts and last
occurrence. Do not scan raw logs across the historical window.
