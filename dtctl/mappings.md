# Known Dynatrace service mappings

Remove the leading environment and region tags from the target before matching the logical service name. Select the Dynatrace context from the original environment tag: `[prd]` uses `prod`; `[stg]`, `[qat]`, and `[dev]` use `nonprod`. Query the same known entity ID in that selected context; assume it is present in both contexts and every region.

| Logical service | Service entity ID | Debugging notes |
| --- | --- | --- |
| `sf-item` | `SERVICE-E8F750E0328DD297` | [sf-item](services/sf-item.md) |
| `agentic-commerce-notifier` | `SERVICE-96B2F23C4556A54F` | [agentic-commerce-notifier](services/agentic-commerce-notifier.md) |
| `agentic-commerce-orchestrator` | `SERVICE-E5986BAFC3F56E4C` | [agentic-commerce-orchestrator](services/agentic-commerce-orchestrator.md) |
| `chewy-api-router` | `SERVICE-592C600D2FAD64FA` | [chewy-api-router](services/chewy-api-router.md) |

Read the linked notes only when debugging that logical service. Add one entity ID per newly verified logical service; keep service-specific behavior out of this index.
