import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { parse as parseYaml } from "yaml";
import { z } from "zod";

type ServiceRecord = {
  repoName: string;
  repoPath: string;
  descriptionPath: string;
  description: string;
  summary: string;
};

type ServiceCatalog = {
  services: ServiceRecord[];
  warnings: string[];
};

type ServiceConfig = {
  source: string;
  servicePaths: string[];
};

const CONFIG_BASENAME = "services.config.yaml";
const SERVICE_PATHS_ENV = "SERVICE_CATALOG_PATHS";

const configSchema = z.object({
  servicePaths: z.array(z.string()).nonempty("servicePaths cannot be empty")
});

function validateServicePaths(servicePaths: string[]): string[] {
  const parsed = configSchema.parse({ servicePaths }).servicePaths;
  const invalid = parsed.filter((servicePath) => !path.isAbsolute(servicePath));

  if (invalid.length > 0) {
    throw new Error(
      `All configured service paths must be absolute. Invalid values: ${invalid.join(", ")}`
    );
  }

  return parsed;
}

function readEnvironmentPaths(): string[] | undefined {
  const raw = process.env[SERVICE_PATHS_ENV]?.trim();
  if (!raw) {
    return undefined;
  }

  const servicePaths = raw
    .split(path.delimiter)
    .map((servicePath) => servicePath.trim())
    .filter(Boolean);

  return validateServicePaths(servicePaths);
}

async function resolveConfig(): Promise<ServiceConfig> {
  const environmentPaths = readEnvironmentPaths();
  if (environmentPaths) {
    return {
      source: SERVICE_PATHS_ENV,
      servicePaths: environmentPaths
    };
  }

  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const searchDirs = [...new Set([scriptDir, path.resolve(scriptDir, ".."), process.cwd()])];

  for (const dir of searchDirs) {
    const candidate = path.resolve(dir, CONFIG_BASENAME);
    try {
      const raw = await fs.readFile(candidate, "utf8");
      const parsed = configSchema.parse(parseYaml(raw));
      return {
        source: candidate,
        servicePaths: validateServicePaths(parsed.servicePaths)
      };
    } catch (error) {
      const code =
        typeof error === "object" && error !== null && "code" in error
          ? String(error.code)
          : undefined;
      if (code !== "ENOENT") {
        throw error;
      }
    }
  }

  throw new Error(
    `No service catalog configuration found. Set ${SERVICE_PATHS_ENV} or add ${CONFIG_BASENAME} in one of: ${searchDirs.join(", ")}.`
  );
}

function getSummary(markdown: string): string {
  const lines = markdown
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith("#"));

  if (lines.length === 0) {
    return "";
  }

  const joined = lines.join(" ");
  return joined.length > 280 ? `${joined.slice(0, 277)}...` : joined;
}

async function loadCatalog(config: ServiceConfig): Promise<ServiceCatalog> {
  const warnings: string[] = [];
  const services: ServiceRecord[] = [];

  for (const repoPath of config.servicePaths) {
    const repoName = path.basename(repoPath);
    const descriptionPath = path.join(repoPath, "service_description.md");

    try {
      const description = await fs.readFile(descriptionPath, "utf8");
      services.push({
        repoName,
        repoPath,
        descriptionPath,
        description,
        summary: getSummary(description)
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      warnings.push(`Skipped "${repoName}" (${repoPath}): ${message}`);
    }
  }

  return { services, warnings };
}

function scoreService(record: ServiceRecord, query: string): number {
  const q = query.trim().toLowerCase();
  const repo = record.repoName.toLowerCase();
  const desc = record.description.toLowerCase();
  const tokens = q.split(/\s+/).filter(Boolean);

  let score = 0;
  if (repo === q) score += 100;
  if (repo.includes(q)) score += 60;
  if (desc.includes(q)) score += 40;

  for (const token of tokens) {
    if (repo.includes(token)) score += 20;
    if (desc.includes(token)) score += 5;
  }

  return score;
}

function asTextPayload(payload: unknown): { content: Array<{ type: "text"; text: string }> } {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(payload, null, 2)
      }
    ]
  };
}

async function createServer(config: ServiceConfig): Promise<McpServer> {
  const server = new McpServer({
    name: "service-catalog",
    version: "0.1.0"
  });

  server.tool(
    "list_services",
    "List all configured repositories that expose a service_description.md file.",
    {},
    async () => {
      const catalog = await loadCatalog(config);

      return asTextPayload({
        config_source: config.source,
        total: catalog.services.length,
        warnings: catalog.warnings,
        services: catalog.services.map((service) => ({
          repo_name: service.repoName,
          path: service.repoPath,
          summary: service.summary
        }))
      });
    }
  );

  server.tool(
    "get_service",
    "Get details for one repository by repo_name.",
    {
      repo_name: z.string().min(1)
    },
    async ({ repo_name }) => {
      const catalog = await loadCatalog(config);
      const target = catalog.services.find((service) => service.repoName === repo_name);

      if (!target) {
        return asTextPayload({
          error: `No service found for repo_name "${repo_name}".`,
          warnings: catalog.warnings,
          available_repo_names: catalog.services.map((service) => service.repoName)
        });
      }

      return asTextPayload({
        repo_name: target.repoName,
        path: target.repoPath,
        description_path: target.descriptionPath,
        description_markdown: target.description,
        warnings: catalog.warnings
      });
    }
  );

  server.tool(
    "find_services",
    "Find repositories by searching repo_name and service_description.md content.",
    {
      query: z.string().min(1)
    },
    async ({ query }) => {
      const catalog = await loadCatalog(config);
      const ranked = catalog.services
        .map((service) => ({
          service,
          score: scoreService(service, query)
        }))
        .filter((entry) => entry.score > 0)
        .sort((a, b) => b.score - a.score);

      return asTextPayload({
        query,
        total_matches: ranked.length,
        warnings: catalog.warnings,
        matches: ranked.map((entry) => ({
          repo_name: entry.service.repoName,
          path: entry.service.repoPath,
          score: entry.score,
          summary: entry.service.summary
        }))
      });
    }
  );

  return server;
}

async function main(): Promise<void> {
  const config = await resolveConfig();
  const server = await createServer(config);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  process.stderr.write(`Failed to start server: ${message}\n`);
  process.exit(1);
});
