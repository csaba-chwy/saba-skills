# Known Dynatrace service mappings

Remove the leading environment and region tags from the target before matching the logical service name. Select the column from the environment tag: `[prd]` uses `prod`; `[stg]`, `[qat]`, and `[dev]` use `nonprod`. Within that column, use an entity ID only when its environment and region exactly match the target. A dash means to resolve the full tagged service name dynamically.

| Logical service | `nonprod` entity IDs | `prod` entity IDs | Debugging notes |
| --- | --- | --- | --- |
| `sf-item` | `[stg][use1]`: `SERVICE-E8F750E0328DD297` | — | [sf-item](services/sf-item.md) |
| `agentic-commerce-notifier` | `[stg][use1]`: `SERVICE-96B2F23C4556A54F` | — | [agentic-commerce-notifier](services/agentic-commerce-notifier.md) |
| `agentic-commerce-orchestrator` | `[stg][use1]`: `SERVICE-E5986BAFC3F56E4C` | — | [agentic-commerce-orchestrator](services/agentic-commerce-orchestrator.md) |
| `chewy-api-router` | — | `[prd][use1]`: `SERVICE-592C600D2FAD64FA` | [chewy-api-router](services/chewy-api-router.md) |

Read the linked notes only when debugging that logical service. Add newly verified entity IDs to the appropriate context column with their exact environment and region; keep service-specific behavior out of this index.
