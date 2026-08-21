#!/usr/bin/env python3
"""Print a bounded Davis problem summary for one logical service."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import sys
from typing import Mapping, Sequence

from build_logs_events_link import build_link
from build_service_problem_query import (
    MAX_PROBLEMS,
    MAX_SERVICE_ENTITIES,
    PROBLEM_STATUSES,
    build_service_entities_query,
    build_service_problems_query,
)
from build_service_rundown_query import ENVIRONMENTS
from run_service_rundown import (
    CommandRunner,
    RundownError,
    _run,
    query_records,
    resolve_window,
    verify_context,
)


@dataclass(frozen=True)
class ServiceEntity:
    name: str
    entity_id: str
    requests: int


@dataclass(frozen=True)
class DavisProblem:
    start: str
    end: str | None
    display_id: str
    name: str
    category: str | None
    status: str
    affected_users: int | None
    affected_entities: int | None
    root_cause_id: str | None
    root_cause_name: str | None


@dataclass(frozen=True)
class ServiceProblemSummary:
    environment: str
    service: str
    context: str
    start: str
    end: str
    lookback: str
    requested_status: str
    entities: tuple[ServiceEntity, ...]
    problems: tuple[DavisProblem, ...]
    link: str
    problem_query_skipped: bool = False

    @property
    def active_count(self) -> int:
        return sum(problem.status == "ACTIVE" for problem in self.problems)

    @property
    def entity_cap_reached(self) -> bool:
        return len(self.entities) == MAX_SERVICE_ENTITIES


def _optional_string(record: Mapping[str, object], name: str) -> str | None:
    value = record.get(name)
    return value if isinstance(value, str) and value else None


def _required_string(record: Mapping[str, object], name: str) -> str:
    value = _optional_string(record, name)
    if value is None:
        raise RundownError(f"Dynatrace result is missing string field {name}")
    return value


def _optional_integer(record: Mapping[str, object], name: str) -> int | None:
    value = record.get(name)
    if value is None:
        return None
    if isinstance(value, str) and value.isdigit():
        return int(value)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RundownError(f"Dynatrace result has invalid numeric field {name}")
    return round(value)


def _entities(records: Sequence[Mapping[str, object]]) -> tuple[ServiceEntity, ...]:
    entities: list[ServiceEntity] = []
    seen: set[str] = set()
    for record in records:
        entity_id = _optional_string(record, "dt.entity.service")
        name = _optional_string(record, "service.name")
        requests = _optional_integer(record, "requests")
        if entity_id is None or name is None or requests is None:
            if all(
                record.get(field) is None
                for field in ("dt.entity.service", "service.name", "requests")
            ):
                continue
            raise RundownError("Dynatrace returned an incomplete service entity")
        if entity_id not in seen:
            entities.append(ServiceEntity(name, entity_id, requests))
            seen.add(entity_id)
    return tuple(entities)


def _problems(records: Sequence[Mapping[str, object]]) -> tuple[DavisProblem, ...]:
    return tuple(
        DavisProblem(
            start=_required_string(record, "event.start"),
            end=_optional_string(record, "event.end"),
            display_id=_required_string(record, "display_id"),
            name=_required_string(record, "event.name"),
            category=_optional_string(record, "event.category"),
            status=_required_string(record, "event.status"),
            affected_users=_optional_integer(
                record, "dt.davis.affected_users_count"
            ),
            affected_entities=_optional_integer(record, "affected_entity_count"),
            root_cause_id=_optional_string(record, "root_cause_entity_id"),
            root_cause_name=_optional_string(record, "root_cause_entity_name"),
        )
        for record in records
    )


def execute_problem_summary(
    *,
    environment: str,
    service: str,
    lookback: str = "1d",
    end_time: str | None = None,
    status: str = "all",
    limit: int = 10,
    environ: Mapping[str, str] | None = None,
    runner: CommandRunner = _run,
) -> ServiceProblemSummary:
    if status not in PROBLEM_STATUSES:
        raise ValueError("status must be one of: " + ", ".join(PROBLEM_STATUSES))
    if not 1 <= limit <= MAX_PROBLEMS:
        raise ValueError(f"limit must be between 1 and {MAX_PROBLEMS}")
    start, end = resolve_window(lookback, end_time=end_time)
    context, environment_url = verify_context(
        environment,
        environ=environ if environ is not None else os.environ,
        runner=runner,
    )

    entity_dql = build_service_entities_query(
        environment=environment,
        service=service,
        start=start,
        end=end,
    )
    entities = _entities(query_records(runner, context, entity_dql))
    if not entities:
        return ServiceProblemSummary(
            environment=environment,
            service=service,
            context=context,
            start=start,
            end=end,
            lookback=lookback,
            requested_status=status,
            entities=(),
            problems=(),
            link=build_link(environment_url, entity_dql),
            problem_query_skipped=True,
        )

    problem_dql = build_service_problems_query(
        entity_ids=tuple(entity.entity_id for entity in entities),
        start=start,
        end=end,
        status=status,
        limit=limit,
    )
    problems = _problems(
        query_records(
            runner,
            context,
            problem_dql,
            scan_limit_gbytes=5,
        )
    )
    return ServiceProblemSummary(
        environment=environment,
        service=service,
        context=context,
        start=start,
        end=end,
        lookback=lookback,
        requested_status=status,
        entities=entities,
        problems=problems,
        link=build_link(environment_url, problem_dql),
    )


def render_markdown(summary: ServiceProblemSummary) -> str:
    lines = [
        f"### `[{summary.environment}]{summary.service}` Davis problems — "
        f"last {summary.lookback}",
        f"`{summary.context}` · `{summary.start}` to `{summary.end}`",
        "",
    ]
    if summary.problem_query_skipped:
        lines.extend(
            (
                "No request-count service entities matched this logical service. "
                "The problem lookup was skipped to avoid a tenant-wide scan.",
                "",
                f"[Open the exact entity query in Dynatrace]({summary.link})",
            )
        )
        return "\n".join(lines)

    lines.append(
        f"- Problems returned: **{len(summary.problems)}** "
        f"(**{summary.active_count} active**)"
    )
    entity_note = (
        " — query cap reached; lower-traffic entities may be omitted"
        if summary.entity_cap_reached
        else ""
    )
    lines.append(
        f"- Matched service entities: **{len(summary.entities)}**{entity_note}"
    )
    if not summary.problems:
        lines.append("- No matching Davis problems were observed in the window.")
    else:
        lines.extend(("", "Problems:"))
        for problem in summary.problems:
            category = f" · {problem.category}" if problem.category else ""
            impact_parts = []
            if problem.affected_users is not None:
                impact_parts.append(f"{problem.affected_users:,} affected users")
            if problem.affected_entities is not None:
                impact_parts.append(f"{problem.affected_entities:,} affected entities")
            impact = f" · {', '.join(impact_parts)}" if impact_parts else ""
            lines.append(
                f"- `{problem.display_id}` · **{problem.status}**{category} — "
                f"{problem.name}{impact}"
            )
            root_cause = problem.root_cause_name or problem.root_cause_id
            if root_cause:
                lines.append(f"  - Davis root cause: `{root_cause}`")
    lines.extend(("", f"[Open the exact problem query in Dynatrace]({summary.link})"))
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize service-scoped Davis problems without raw log scans."
    )
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--lookback", default="1d")
    parser.add_argument("--end-time", help="Optional RFC 3339 end time.")
    parser.add_argument("--status", choices=PROBLEM_STATUSES, default="all")
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        summary = execute_problem_summary(
            environment=args.environment,
            service=args.service,
            lookback=args.lookback,
            end_time=args.end_time,
            status=args.status,
            limit=args.limit,
        )
    except (RundownError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    print(render_markdown(summary))


if __name__ == "__main__":
    main()
