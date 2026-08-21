# Efficient DQL authoring

Read this reference only for novel DQL, query optimization, field discovery, or
invalid-query recovery. Do not load it for the bundled rundown, error, problem,
or regression runners.

This reference adapts the Dynatrace
[`dt-dql-essentials`](https://github.com/Dynatrace/dynatrace-for-ai/tree/main/skills/dt-dql-essentials)
skill at commit `ec2fb22d95167539dda7811b4347543431dce824` under Apache-2.0.
Tenant-observed fields and the safeguards in this skill take precedence over
generic examples.

## Author once, execute once

1. Reuse a bundled Python runner or query builder when one matches the question.
2. Select the metric or data object that directly answers the question.
3. Fix an absolute UTC timeframe and the narrowest confirmed service selector.
4. Put selective filters immediately after `fetch`; select only required fields.
5. Combine related aggregations in one query and group only on necessary,
   low-cardinality dimensions.
6. Execute once. Use `dtctl verify query` only after an invalid-DQL response, as
   specified in [raw-query-controls.md](raw-query-controls.md).
7. When the query becomes repeatable, add a parameterized Python builder and
   runner with tests instead of retaining another prompt-only recipe.

## Discover instead of guessing

Use one bounded discovery query only when a required field or model is unknown:

```dql
fetch dt.semantic_dictionary.fields
| filter startsWith(name, "http.")
| fields name, type, stability
| dedup name
| limit 100
```

Use `describe <data-object>` for fields on a specific table. For metric
dimensions, use `metrics` against the exact metric and service selector. Do not
replace locally validated `service.name`, `dt.entity.service`, log, or workload
selectors merely because a generic reference recommends a newer namespace.

## High-value syntax checks

| Intent | Correct DQL shape |
| --- | --- |
| Static membership | `in(field, {"a", "b"})` |
| Group on several fields | `by: {field_a, field_b}` |
| Equality | `field == "value"` |
| Log severity | `loglevel == "ERROR"` |
| String wildcard | `matchesValue(field, "*value*")` |
| String substring | `contains(field, "value")` |
| Collapse a metric to one value | `sum(metric, scalar: true)` |
| Collapse an existing series | `arraySum(series)` |
| Exact trace ID | `trace.id == toUid("32-HEX-CHARACTERS")` |
| Span chronology | Sort on `start_time`, not `timestamp` |

Array fields need array-aware membership or an explicit `expand`; scalar `==`
can silently return no results. Alias calculated grouping keys instead of relying
on their normalized names. Fields added by `lookup` and `join` are prefixed
unless the query explicitly selects or renames them.

## Cost controls

- Prefer metrics for totals, rates, and percentiles; query raw logs or spans only
  for evidence the metric result cannot supply.
- Apply the shortest useful timeframe at the source.
- Filter before parsing, aggregation, sorting, or joins.
- Avoid grouping on trace IDs, request IDs, user IDs, raw content, or other
  unbounded dimensions.
- A result `limit` controls output size, not scanned bytes. Follow the 5 GB raw
  starting cap and sampling rules in [raw-query-controls.md](raw-query-controls.md).
- Prefer one query with combined aggregations over several scans of the same
  data and timeframe.

## Stop conditions

Stop when the returned values answer the explicit question and a tenant-correct
Dynatrace link has been generated. Do not add schema discovery, another
telemetry source, or raw examples merely for completeness.
