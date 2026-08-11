# Service Catalog MCP Server

TypeScript MCP server that indexes multiple repositories and exposes service discovery tools over stdio.

Each configured repository path is expected to contain a `service_description.md` file at its root.

## Tools

- `list_services()` returns all discovered services, summaries, and `last_verified` dates.
- `get_service(repo_name)` returns the full `service_description.md` and its verification date for one repository.
- `find_services(query)` searches repository names and descriptions and returns verification dates with matches.

The verification date comes from the generated `Last verified: YYYY-MM-DD` line. Planning skills should use it as a freshness signal and confirm important claims against current code when it is missing or too old for the change being planned.

## Configuration

Prefer the `SERVICE_CATALOG_PATHS` environment variable. Separate multiple absolute paths with the platform path delimiter (`:` on macOS/Linux and `;` on Windows).

```bash
export SERVICE_CATALOG_PATHS="/home/alex/projects/example-api:/home/alex/projects/example-worker"
```

When the variable is unset, the server falls back to `services.config.yaml`:

```yaml
servicePaths:
  - /home/alex/projects/example-api
  - /home/alex/projects/example-worker
```

The repository’s root `.env` is intentionally ignored by Git. Source it before starting the server when it contains the environment-specific paths:

```bash
set -a
source ../.env
set +a
```

All paths must be absolute. `repo_name` is inferred from each directory basename.

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start
```

After building, add the server to Codex:

```bash
codex mcp add service-catalog -- node /absolute/path/to/service-catalog-mcp/dist/index.js
```

For development:

```bash
npm run dev
```
