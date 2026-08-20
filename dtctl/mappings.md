# Known Dynatrace service mappings

Remove the leading environment and region tags from the target before matching the logical service name. Select the context and Dynatrace environment URL from the original environment tag: `[prd]` uses `prod` with `DTCTL_PROD_ENVIRONMENT`; `[stg]`, `[qat]`, and `[dev]` use `nonprod` with `DTCTL_NONPROD_ENVIRONMENT`. Authenticate the selected URL into its matching read-only context before querying. Use the telemetry stem with `log.source` plus `env` for logical log selection and as the suffix of tagged metric `service.name`; preserve the tags only when an exact workload, service name, or entity fallback is required.

The logical selector templates live in [references/query-strategy.md](references/query-strategy.md), and the shared service behavior lives in [SKILL.md](SKILL.md). Keep every linked service note environment-neutral: it may document a telemetry stem alias, log bucket, or service-specific enrichment behavior, but it must not pin an environment or restate the shared investigation baseline.

| Logical service | Telemetry stem | Entity ID seed | Debugging notes |
| --- | --- | --- | --- |
| `sf-item` | `sf-item` | `SERVICE-E8F750E0328DD297` | [sf-item](services/sf-item.md) |
| `agentic-commerce-notifier` | `agentic-commerce-notifier` | `SERVICE-96B2F23C4556A54F` | [agentic-commerce-notifier](services/agentic-commerce-notifier.md) |
| `agentic-commerce-orchestrator` | `agentic-commerce-orchestrator` | `SERVICE-E5986BAFC3F56E4C` | [agentic-commerce-orchestrator](services/agentic-commerce-orchestrator.md) |
| `chewy-api-router` | `chewy-api-router` | `SERVICE-592C600D2FAD64FA` | [chewy-api-router](services/chewy-api-router.md) |
| `cart-a` | `cart-a` | `SERVICE-032E4C5EE9101D63` | [cart-a](services/cart-a.md) |
| `cart-b` | `cart-b` | `SERVICE-BB0EFB16FAAC4EB8` | [cart-b](services/cart-b.md) |
| `checkout-a` | `checkout-a` | `SERVICE-CD10D15F54A9F272` | [checkout-a](services/checkout-a.md) |
| `checkout-b` | `checkout-b` | `SERVICE-1CE859C27F118D71` | [checkout-b](services/checkout-b.md) |
| `cart-spa` | `cart-spa` | `SERVICE-4AE05397219E7068` | [cart-spa](services/cart-spa.md) |
| `purchase-app` | `purchaseapp` | `SERVICE-271E3BD4C197C4E5` | [purchase-app](services/purchase-app.md) |
| `chewy-portal` | `chewy-portal` | `SERVICE-7534E417EEEFFB45` | [chewy-portal](services/chewy-portal.md) |

Treat an entity ID as a fallback seed for spans or ambiguous enrichment, not an environment selector or permanent identity. Validate it in the selected context, fall back to exact-name discovery when it has no data, and rank duplicate active IDs by request volume and workload or pod identity. Read the linked notes only when debugging that logical service; keep service-specific behavior out of this index.
