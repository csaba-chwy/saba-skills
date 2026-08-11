---
name: dtctl
description: Investigate incidents, debug performance issues, analyze logs, and manage observability resources in Dynatrace using the dtctl CLI. Use this skill whenever the user asks about error rates, latency spikes, service health, crash-looping pods, web vitals, SLO status, open problems, root cause analysis, log patterns, trace analysis, or building dashboards — even if they don't mention Dynatrace by name. Also covers DQL queries, workflow management, notebook and dashboard creation, settings configuration, and any operations against a Dynatrace environment.
---

# Dynatrace Control with dtctl

Operate `dtctl`, the kubectl-style CLI for Dynatrace. This skill teaches core dtctl command patterns and operations.

## Recommended Initialization

At the start of a task, run these checks to establish context and permissions:

```bash
# Discover all available commands, flags, and resources
dtctl commands --brief -o json

# Show current context
dtctl config current-context

# Show context details
dtctl config describe-context $(dtctl config current-context) --plain

# Show auth context: token type (OAuth vs API/platform) and safety level
dtctl auth status --plain
```

This displays:
- Current context name and environment URL
- Safety level (readonly, readwrite-mine, readwrite-all, dangerously-unrestricted)
- Token type (OAuth vs API/platform token)

> **Note:** Do not use `dtctl auth whoami` to verify a connection. It performs an
> identity lookup against the platform metadata API and needs an OAuth/JWT token
> with the `app-engine:apps:run` scope; with a plain API token or a read-scoped
> platform token it returns a spurious 403 even though read access works fine.
> Confirm connectivity with your first real query (`dtctl get ...` or
> `dtctl query ...`), not with an identity probe.

## DQL Reference Usage

Before writing, modifying, or executing any DQL that fetches Dynatrace data (for example via `dtctl query`, `dtctl wait query`, or query files), you MUST consult `references/DQL-reference.md` and follow its documented syntax and templates.

If there is any conflict between memory/assumptions and the reference, prefer the reference.

## Query Safety And Cost Controls

Every data-fetching DQL query MUST be narrowly scoped before it is run. A `limit` only limits returned records; it does **not** limit the amount of Grail data scanned.

1. Resolve the target to explicit entity IDs or another selective attribute before querying. Do not begin with a tenant-wide name, content, or error search.
2. Put a bounded `from:`/`to:` range on every `fetch`. Start with the smallest useful window—normally `now()-15m` for request, log, and trace investigation, or `now()-1h` when a short trend is needed.
3. Filter on the target entity before sorting, aggregation, or selecting wide fields. Return only the fields needed for the next investigation step.
4. Include a final `limit`; use `20` for initial evidence and do not exceed `100` without a stated reason.
5. Validate first: `dtctl verify query '<DQL>' --plain`. Then execute with an explicit scan cap, for example `dtctl query '<DQL>' --default-scan-limit-gbytes 5 -o json --plain`.
6. If Dynatrace reports a scan-limit warning or returns no result, narrow the time range and filter first. Do not raise the cap, use `-1`, or run a broader query without the user's approval.

For a window wider than two hours, an unbounded aggregation, a query that could scan a custom bucket, or a scan cap above 20 GB, explain the expected cost and get the user's approval first.

## Direct Dynatrace Links

When investigation results are useful to the user, provide direct Dynatrace links for the retrieved trace, log, or event rather than a guessed URL.

1. Discover supported navigation targets with `dtctl get intents -o json --plain`, then invoke the resolved target with `dtctl open intent <app/intent> --data key=value`. Use the exact identifier returned by the query (for example, a trace ID, log record ID, event ID, or entity ID) and the data key expected by that intent.
2. If `dtctl open` opens the UI instead of returning a URL, use an available in-app Browser or Chrome control tool to read the resulting address and include that exact URL in the response.
3. Label links clearly as **Trace**, **Logs**, or **Event**, and include only the least-sensitive context needed to make the link useful.
4. Never fabricate an application path, infer undocumented query parameters, or place tokens, credentials, or sensitive record content in a link. If access or a navigation intent is unavailable, say so and provide the record ID and the command used to retrieve it instead.

## Prerequisites

If dtctl is not installed or not working, see [references/troubleshooting.md](references/troubleshooting.md) for installation and setup.

## Resources & Commands

### Available Resources

dtctl uses a uniform pattern for all resource types. Discover schema from actual output with `dtctl describe <resource> <id> -o json --plain`.

| Resource | Aliases |
|----------|---------|
| analyzer | analyzers |
| app | apps |
| aws connection | - |
| aws monitoring | - |
| azure connection | - |
| azure monitoring | - |
| bucket | bkt |
| copilot-skill | copilot-skills |
| dashboard | dash |
| edgeconnect | ec |
| extension | ext, extensions |
| extension-config | extcfg, extension-configs |
| function | fn, func |
| gcp connection | - |
| gcp monitoring | - |
| group | groups |
| intent | intents |
| lookup | lookups, lkup |
| notebook | nb |
| notification | notifications |
| sdk-version | sdk-versions |
| settings | setting |
| settings-schema | schema |
| slo | - |
| slo-template | slo-templates |
| trash | deleted |
| user | users |
| workflow | wf |
| workflow-execution | wfe |

Use IDs whenever possible instead of names to avoid ambiguity.

### Command Verbs

| Verb | Description | Example |
|------|-------------|---------|
| **get** | List resources | `dtctl get workflows --mine` |
| **describe** | Show resource details | `dtctl describe workflow <id>` |
| **edit** | Edit resource interactively | `dtctl edit dashboard <id>` |
| **apply** | Create/update from file | `dtctl apply -f workflow.yaml --set env=prod` |
| **delete** | Delete resource | `dtctl delete workflow <id>` |
| **exec** | Execute workflow/function/analyzer/copilot | `dtctl exec workflow <id>` |
| **query** | Run bounded DQL query | `dtctl query "fetch logs, from:now()-15m \| filter dt.entity.service == \"SERVICE-xxx\" \| limit 20" --default-scan-limit-gbytes 5` |
| **logs** | Print resource logs | `dtctl logs workflow-execution <id>` |
| **wait** | Wait for conditions | `dtctl wait query "fetch logs, from:now()-15m \| limit 1" --for=any` |
| **history** | Show document history | `dtctl history dashboard <id>` |
| **restore** | Restore document version | `dtctl restore dashboard <id> --version 3` |
| **share** | Share document | `dtctl share dashboard <id> --user email@example.com` |
| **unshare** | Remove sharing | `dtctl unshare dashboard <id> --user email@example.com` |
| **find** | Discover resources | `dtctl find intents --data trace.id=abc` |
| **open** | Open in browser | `dtctl open intent <app/intent> --data key=value` |
| **diff** | Compare resources | `dtctl diff -f workflow.yaml` |
| **verify** | Validate without executing | `dtctl verify query 'fetch logs, from:now()-15m | limit 20' --fail-on-warn` |
| **commands** | List all commands (machine-readable) | `dtctl commands --brief -o json` |

## Key Concepts for AI Agents

### Output Modes

```bash
# Agent envelope mode (auto-detected in AI environments)
-A, --agent      # Structured JSON envelope with ok/result/error/context
--no-agent       # Opt out of auto-detected agent mode

# Machine-readable formats (use these for AI agents)
-o json          # JSON output
-o yaml          # YAML output
-o csv           # CSV output
-o chart         # ASCII chart (for time series)
-o sparkline     # ASCII sparkline (for time series)
-o barchart      # ASCII bar chart (for time series)

# Human-readable formats
-o table         # Table format (default)
-o wide          # Wide table with more columns

# Always use --plain flag for AI consumption (implied by --agent)
--plain          # Strips colors and prompts, best for parsing
```

**For AI agents, prefer:** `dtctl <command> --agent` (auto-detected) or `dtctl <command> -o json --plain`

The `--agent` envelope provides structured metadata alongside results:

```json
{
  "ok": true,
  "result": [ ... ],
  "context": {
    "verb": "get", "resource": "workflow",
    "total": 5, "has_more": false,
    "suggestions": ["Run 'dtctl describe workflow <id>' for details"]
  }
}
```

### Template Variables

In YAML/DQL files, use Go template syntax:

```yaml
# workflow.yaml
title: "{{.environment}} Deployment"
owner: "{{.team}}"
trigger:
  schedule:
    cron: "{{.schedule | default "0 0 * * *"}}"
```

```dql
# query.dql
fetch logs, from:now()-{{.timerange | default "15m"}}
| filter host.name == "{{.host}}"
| fields timestamp, content, loglevel
| limit {{.limit | default "20"}}
```

Execute with: `dtctl apply -f file.yaml --set environment=prod --set team=platform`

### Copilot, Functions, Analyzers

```bash
# Copilot skills
dtctl get copilot-skills -o json --plain

# Functions
dtctl get functions -o json --plain
dtctl exec function <id-or-name> --payload '{"key":"value"}' --plain

# Analyzers
dtctl get analyzers -o json --plain
dtctl exec analyzer <id-or-name> --input '{"timeframe":"now-2h"}' --plain
```

Prefer `get ... -o json --plain` first, then `describe`/`exec` with explicit IDs.

### Authentication & Permissions

```bash
# Check auth context and permissions
dtctl auth status --plain
dtctl auth can-i create workflows
dtctl auth can-i delete dashboards
```

Use `can-i` to verify permissions before attempting operations.

## Quick Reference: DQL Queries

**Required workflow for DQL data fetching:**
1. First consult `references/DQL-reference.md`
2. Build/validate the query using the documented patterns
3. Execute with `dtctl query ... --default-scan-limit-gbytes 5 -o json --plain` (or `dtctl wait query ...` when waiting for results)

```bash
# Inline query
dtctl query "fetch logs, from:now()-15m | filter dt.entity.service == 'SERVICE-xxx' | filter status='ERROR' | fields timestamp, content, status | sort timestamp desc | limit 20" --default-scan-limit-gbytes 5 -o json --plain

# Query from file with variables
dtctl query -f query.dql --set host=h-123 --set timerange=15m --set limit=20 --default-scan-limit-gbytes 5 -o json --plain

# Wait for query results
dtctl wait query "fetch spans, from:now()-15m | filter test_id='test-123' | limit 1" --for=count=1 --timeout 5m

# Query with chart output
dtctl query "timeseries avg(dt.host.cpu.usage), from:now()-2h, interval:5m" --default-scan-limit-gbytes 5 -o chart --plain
```



## Dashboards

For full examples and field-level gotchas, see [references/resources/dashboards.md](references/resources/dashboards.md).

Create/update: `dtctl apply -f dashboard.yaml --plain`. Export for reference: `dtctl get dashboard <id> -o yaml --plain`.

### YAML skeleton

```yaml
name: "Dashboard Name"
type: dashboard
content:
  annotations: []
  importedWithCode: false
  settings:
    defaultTimeframe:
      enabled: true
      value: { from: now()-2h, to: now() }
  layouts:
    "1":                    # string key, must match a tile key
      x: 0                 # 24-column grid (full=24, half=12, third=8)
      "y": 0               # MUST quote "y" to avoid YAML boolean parse
      w: 12
      h: 6
  tiles:
    "1":
      title: "Tile Title"
      type: data            # data | markdown
      query: |
        fetch logs, from:now()-15m | filter dt.entity.service == "{{.service_id}}" | fields timestamp, content, loglevel | sort timestamp desc | limit 20
      visualization: lineChart
      visualizationSettings:
        autoSelectVisualization: false
      davis: { enabled: false, davisVisualization: { isAvailable: true } }
```

### Tile types & visualizations

- **`type: data`** — DQL tile with `query` + `visualization`: `singleValue`, `lineChart`, `areaChart`, `barChart`, `pieChart`, `table`, `honeycomb`, `scatterplot`
- **`type: markdown`** — static text via `content` field (supports markdown)

For detailed visualizationSettings (singleValue, charts, tables, thresholds, unit overrides), see [references/resources/dashboards.md](references/resources/dashboards.md).

### Gotchas
- Always set `davis.enabled: false` on data tiles.
- Use `makeTimeseries` for log/span time series; `timeseries` for metrics.
- `version` field warning on create is benign.
- No `id` field → creates new; with `id` field → updates existing.

## Common Issues

**Name resolution ambiguity:**
- If a name matches multiple resources, dtctl will fail
- Solution: Use IDs instead of names
- Find ID: `dtctl get <resource> -o json --plain | jq -r '.[] | "\(.id) | \(.name)"'`

**Permission denied:**
- Check token scopes: https://github.com/dynatrace-oss/dtctl/blob/main/docs/TOKEN_SCOPES.md
- Verify permissions: `dtctl auth can-i <verb> <resource>`
- Check safety level: `dtctl config describe-context $(dtctl config current-context) --plain`

**Context/safety blocks:**
- Destructive operations may be blocked by safety level
- Switch context: `dtctl config use-context <name>`
- Adjust safety level when creating context

## Additional Resources

- **Troubleshooting**: [references/troubleshooting.md](references/troubleshooting.md)
- **Multi-tenant setup**: [references/config-management.md](references/config-management.md)
- **DQL syntax and templates**: [references/DQL-reference.md](references/DQL-reference.md)
- **Notebooks**: [references/resources/notebooks.md](references/resources/notebooks.md)
- **Extensions**: [references/resources/extensions.md](references/resources/extensions.md)
- **CLI help**: `dtctl --help`, `dtctl <command> --help`

## Safety Reminders

- Use `--plain` for machine/AI consumption
- Confirm context + safety level before destructive ops; prefer `get/describe` first
- Bound every data fetch by time, target filter, result limit, and `--default-scan-limit-gbytes`; a `limit` alone does not control scan cost
- On scan-limit warnings, narrow the query instead of increasing the cap without approval
- Generate trace, log, and event links only from a verified Dynatrace intent or the URL opened in an authenticated browser session
- Use `--mine` flag to filter resources you own
- For multi-tenant work, see [references/config-management.md](references/config-management.md)
