# Known Dynatrace service mappings

Remove the leading environment and region tags from the target before matching the logical service name. Select the context and Dynatrace environment URL from the original environment tag: `[prd]` uses `prod` with `DTCTL_PROD_ENVIRONMENT`; `[stg]`, `[qat]`, and `[dev]` use `nonprod` with `DTCTL_NONPROD_ENVIRONMENT`. Authenticate the selected URL into its matching read-only context before querying. Use the telemetry stem with `log.source` plus `env` for logical log selection and as the suffix of tagged metric `service.name`; preserve the tags only when an exact workload, service name, or entity fallback is required.

The logical selector templates live in [references/query-strategy.md](references/query-strategy.md), and the shared service behavior lives in [SKILL.md](SKILL.md). Keep every linked service note environment-neutral: it may document a telemetry stem alias, log bucket, or service-specific enrichment behavior, but it must not pin an environment or restate the shared investigation baseline.

The entity ID seeds below were validated from production `dt.service.request.count` telemetry over the preceding 24 hours on 2026-08-21. Use them to accelerate exact entity queries and span pivots after selecting `prod`; keep the logical selector as the first lookup because entity IDs can change. Nonproduction contexts must resolve and verify their own IDs.

| Logical service | Telemetry stem | Current PRD entity ID seeds | Debugging notes |
| --- | --- | --- | --- |
| `sf-item` | `sf-item` | use1: `SERVICE-4D3CC297F58610EF`<br>use2: `SERVICE-EFAECFC53A8BEA4E` | [sf-item](services/sf-item.md) |
| `agentic-commerce-notifier` | `agentic-commerce-notifier` | use1: `SERVICE-AD47EA2B82D1C920`<br>use2: `SERVICE-0201C71475405912` | [agentic-commerce-notifier](services/agentic-commerce-notifier.md) |
| `agentic-commerce-orchestrator` | `agentic-commerce-orchestrator` | use1: `SERVICE-880DA3BBFCFE8E87`<br>use2: `SERVICE-26EF4F42398F4D91` | [agentic-commerce-orchestrator](services/agentic-commerce-orchestrator.md) |
| `chewy-api-router` | `chewy-api-router` | use1: `SERVICE-592C600D2FAD64FA`<br>use2: `SERVICE-C4F068B8200DD68F` | [chewy-api-router](services/chewy-api-router.md) |
| `cart-a` | `cart-a` | use1: `SERVICE-032E4C5EE9101D63`<br>use2: `SERVICE-8D857702F03F9030` | [cart-a](services/cart-a.md) |
| `cart-b` | `cart-b` | use1: `SERVICE-BB0EFB16FAAC4EB8`<br>use2: `SERVICE-F0892174C452B977` | [cart-b](services/cart-b.md) |
| `checkout-a` | `checkout-a` | use1: `SERVICE-CD10D15F54A9F272`<br>use2: `SERVICE-E4814CE996D214D0` | [checkout-a](services/checkout-a.md) |
| `checkout-b` | `checkout-b` | use1: `SERVICE-1CE859C27F118D71`<br>use2: `SERVICE-53E63590FE02952B` | [checkout-b](services/checkout-b.md) |
| `cart-spa` | `cart-spa` | use1: `SERVICE-4AE05397219E7068`<br>use2: `SERVICE-33771D6ADF857659` | [cart-spa](services/cart-spa.md) |
| `purchase-app` | `purchaseapp` | use1: `SERVICE-271E3BD4C197C4E5`<br>use2: `SERVICE-8397C075AC94D2BB` | [purchase-app](services/purchase-app.md) |
| `chewy-portal` | `chewy-portal` | use1: `SERVICE-7534E417EEEFFB45`, `SERVICE-7351592C7CB79406`<br>use2: `SERVICE-BE05E0093AD378C8`, `SERVICE-BE11B31F34D6E1F6` | [chewy-portal](services/chewy-portal.md) |

Treat an entity ID as a fallback seed for spans or ambiguous enrichment, not an environment selector or permanent identity. Validate it in the selected context, fall back to exact-name discovery when it has no data, and rank duplicate active IDs by request volume and workload or pod identity. When multiple seeds are listed for one region, retain all of them until the requested traffic class is clear. Read the linked notes only when debugging that logical service; keep service-specific behavior out of this index.
