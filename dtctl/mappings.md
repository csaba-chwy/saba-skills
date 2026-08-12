# Known Dynatrace service mappings

Use a mapping only for an exact service-name and environment match. Read the linked service notes only when debugging that service. If a known entity ID returns no data or conflicts with current telemetry, resolve the exact service name again and update this mapping plus its service file when the new behavior is verified.

| Service name | Context | Service entity ID | Debugging notes |
| --- | --- | --- | --- |
| `[stg][use1]sf-item` | `nonprod` | `SERVICE-E8F750E0328DD297` | [sf-item](services/stg-use1-sf-item.md) |
| `[stg][use1]agentic-commerce-notifier` | `nonprod` | `SERVICE-96B2F23C4556A54F` | [agentic-commerce-notifier](services/stg-use1-agentic-commerce-notifier.md) |
| `[stg][use1]agentic-commerce-orchestrator` | `nonprod` | `SERVICE-E5986BAFC3F56E4C` | [agentic-commerce-orchestrator](services/stg-use1-agentic-commerce-orchestrator.md) |
| `[prd][use1]chewy-api-router` | `prod` | `SERVICE-592C600D2FAD64FA` | [chewy-api-router](services/prd-use1-chewy-api-router.md) |
