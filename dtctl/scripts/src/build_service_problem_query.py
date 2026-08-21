#!/usr/bin/env python3
"""Build bounded DQL for service-scoped Davis problem summaries."""

from __future__ import annotations

import argparse
import re

from build_service_rundown_query import (
    build_service_filter,
    validate_absolute_window,
    validate_service_window,
)


ENTITY_ID_RE = re.compile(r"^SERVICE-[A-F0-9]{16}$")
PROBLEM_STATUSES = ("all", "active", "closed")
MAX_SERVICE_ENTITIES = 20
MAX_PROBLEMS = 20


def build_service_entities_query(
    *,
    environment: str,
    service: str,
    start: str,
    end: str,
) -> str:
    """Resolve service entity IDs observed in one request-count metric query."""
    validate_service_window(environment, service, start, end)
    service_filter = build_service_filter(environment, service)
    return "\n".join(
        (
            "timeseries requests = sum(dt.service.request.count, scalar: true), "
            "by: { service.name, dt.entity.service }, "
            f"filter: {{ {service_filter} }}, "
            f'from: "{start}", to: "{end}", nonempty: true',
            "| fields service.name, dt.entity.service, requests",
            "| filter isNotNull(dt.entity.service)",
            "| sort requests desc, service.name asc",
            f"| limit {MAX_SERVICE_ENTITIES}",
        )
    )


def build_service_problems_query(
    *,
    entity_ids: tuple[str, ...],
    start: str,
    end: str,
    status: str = "all",
    limit: int = 10,
) -> str:
    """Return a deduplicated problem query for exact service entity IDs."""
    if not entity_ids:
        raise ValueError("at least one service entity ID is required")
    unique_ids = tuple(dict.fromkeys(entity_ids))
    if len(unique_ids) > MAX_SERVICE_ENTITIES:
        raise ValueError(f"at most {MAX_SERVICE_ENTITIES} service entities are allowed")
    if any(not ENTITY_ID_RE.fullmatch(value) for value in unique_ids):
        raise ValueError("invalid Dynatrace service entity ID")
    if status not in PROBLEM_STATUSES:
        raise ValueError("status must be one of: " + ", ".join(PROBLEM_STATUSES))
    if not 1 <= limit <= MAX_PROBLEMS:
        raise ValueError(f"limit must be between 1 and {MAX_PROBLEMS}")
    validate_absolute_window(start, end)

    entity_set = ", ".join(f'"{value}"' for value in unique_ids)
    lines = [
        f'fetch dt.davis.problems, from: "{start}", to: "{end}"',
        "| filter not(dt.davis.is_duplicate)",
    ]
    if status != "all":
        lines.append(f'| filter event.status == "{status.upper()}"')
    lines.extend(
        (
            f"| filter matchesValue(affected_entity_ids, {{{entity_set}}}) "
            f"or in(root_cause_entity_id, {{{entity_set}}})",
            "| fields event.start, event.end, display_id, event.name, "
            "event.category, event.status, dt.davis.affected_users_count, "
            "root_cause_entity_id, root_cause_entity_name, "
            "affected_entity_count = arraySize(affected_entity_ids)",
            "| dedup display_id",
            "| sort event.start desc",
            f"| limit {limit}",
        )
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build bounded DQL for a service-scoped Davis problem summary."
    )
    parser.add_argument("--entity-id", action="append", required=True)
    parser.add_argument("--from-time", dest="start", required=True)
    parser.add_argument("--to-time", dest="end", required=True)
    parser.add_argument("--status", choices=PROBLEM_STATUSES, default="all")
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        build_service_problems_query(
            entity_ids=tuple(args.entity_id),
            start=args.start,
            end=args.end,
            status=args.status,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
