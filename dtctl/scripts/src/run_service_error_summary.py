#!/usr/bin/env python3
"""Print a fast service error summary with native Dynatrace drill-down links."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import re
import sys
from typing import Mapping, Sequence
from urllib.parse import quote

from build_logs_events_link import build_link, normalize_environment_url
from build_service_rundown_query import (
    ENVIRONMENTS,
    MAX_ERROR_GROUPS,
    build_service_error_totals_query,
    build_top_service_errors_query,
)
from run_service_rundown import (
    CommandRunner,
    RundownError,
    _run,
    query_records,
    resolve_window,
    verify_context,
)


ENTITY_ID_RE = re.compile(r"^SERVICE-[A-F0-9]{16}$")
FAILURE_ANALYSIS_INTENT = "dynatrace.services/view-service-failure-analysis"


@dataclass(frozen=True)
class DeploymentErrors:
    service_name: str
    entity_id: str | None
    requests: int
    failures: int
    failure_analysis_link: str | None

    @property
    def error_rate(self) -> float:
        return 100.0 * self.failures / self.requests if self.requests else 0.0


@dataclass(frozen=True)
class ErrorGroup:
    endpoint: str | None
    http_status: str | None
    failures: int


@dataclass(frozen=True)
class ServiceErrorSummary:
    environment: str
    service: str
    context: str
    start: str
    end: str
    lookback: str
    deployments: tuple[DeploymentErrors, ...]
    top_errors: tuple[ErrorGroup, ...]
    breakdown_link: str

    @property
    def requests(self) -> int:
        return sum(deployment.requests for deployment in self.deployments)

    @property
    def failures(self) -> int:
        return sum(deployment.failures for deployment in self.deployments)

    @property
    def error_rate(self) -> float:
        return 100.0 * self.failures / self.requests if self.requests else 0.0


def _number(record: Mapping[str, object], name: str) -> int:
    value = record.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RundownError(f"Dynatrace result is missing numeric field {name}")
    return round(value)


def build_failure_analysis_link(
    environment_url: str,
    entity_id: str,
    *,
    start: str,
    end: str,
) -> str:
    """Build a tenant-correct Services Failure Analysis intent URL."""
    if not ENTITY_ID_RE.fullmatch(entity_id):
        raise ValueError("invalid Dynatrace service entity ID")
    payload = json.dumps(
        {
            "dt.entity.service": entity_id,
            "dt.timeframe": {"from": start, "to": end},
        },
        separators=(",", ":"),
    )
    base_url = normalize_environment_url(environment_url)
    return f"{base_url}/ui/intent/{FAILURE_ANALYSIS_INTENT}#{quote(payload, safe='')}"


def execute_error_summary(
    *,
    environment: str,
    service: str,
    lookback: str = "1d",
    end_time: str | None = None,
    top: int = 5,
    environ: Mapping[str, str] | None = None,
    runner: CommandRunner = _run,
) -> ServiceErrorSummary:
    if not 1 <= top <= MAX_ERROR_GROUPS:
        raise ValueError(f"top must be between 1 and {MAX_ERROR_GROUPS}")
    start, end = resolve_window(lookback, end_time=end_time)
    context, environment_url = verify_context(
        environment,
        environ=environ if environ is not None else os.environ,
        runner=runner,
    )
    totals_dql = build_service_error_totals_query(
        environment=environment,
        service=service,
        start=start,
        end=end,
    )
    total_records = query_records(runner, context, totals_dql)
    deployments = _deployments_from_records(
        total_records,
        environment_url,
        start,
        end,
    )

    breakdown_dql = build_top_service_errors_query(
        environment=environment,
        service=service,
        start=start,
        end=end,
        limit=top,
    )
    total_failures = sum(deployment.failures for deployment in deployments)
    top_records = (
        query_records(runner, context, breakdown_dql) if total_failures else []
    )
    top_errors = tuple(
        ErrorGroup(
            endpoint=_optional_string(record, "endpoint.name"),
            http_status=_optional_string(record, "http.response.status_code"),
            failures=_number(record, "failures"),
        )
        for record in top_records
    )
    return ServiceErrorSummary(
        environment=environment,
        service=service,
        context=context,
        start=start,
        end=end,
        lookback=lookback,
        deployments=deployments,
        top_errors=top_errors,
        breakdown_link=build_link(environment_url, breakdown_dql),
    )


def _optional_string(record: Mapping[str, object], name: str) -> str | None:
    value = record.get(name)
    return value if isinstance(value, str) and value else None


def _deployments_from_records(
    records: Sequence[Mapping[str, object]],
    environment_url: str,
    start: str,
    end: str,
) -> tuple[DeploymentErrors, ...]:
    grouped: dict[tuple[str, str | None], list[int]] = {}
    for record in records:
        service_name = _optional_string(record, "service.name")
        if service_name is None:
            if all(record.get(field) is None for field in ("service.name", "requests")):
                continue
            raise RundownError("Dynatrace result is missing service.name")
        failed = record.get("failed")
        if not isinstance(failed, bool):
            raise RundownError("Dynatrace result is missing Boolean field failed")
        entity_id = _optional_string(record, "dt.entity.service")
        requests = _number(record, "requests")
        counts = grouped.setdefault((service_name, entity_id), [0, 0])
        counts[0] += requests
        if failed:
            counts[1] += requests

    deployments = []
    for (service_name, entity_id), (requests, failures) in grouped.items():
        link = (
            build_failure_analysis_link(
                environment_url,
                entity_id,
                start=start,
                end=end,
            )
            if entity_id and ENTITY_ID_RE.fullmatch(entity_id)
            else None
        )
        deployments.append(
            DeploymentErrors(
                service_name=service_name,
                entity_id=entity_id,
                requests=requests,
                failures=failures,
                failure_analysis_link=link,
            )
        )
    return tuple(
        sorted(deployments, key=lambda item: (-item.failures, item.service_name))
    )


def render_markdown(summary: ServiceErrorSummary) -> str:
    lines = [
        f"### `[{summary.environment}]{summary.service}` errors — last {summary.lookback}",
        f"`{summary.context}` · `{summary.start}` to `{summary.end}`",
        "",
    ]
    if not summary.deployments:
        lines.extend(
            (
                "No request-count metrics matched this logical service in the window.",
                "",
                f"[Open the exact error query in Dynatrace]({summary.breakdown_link})",
            )
        )
        return "\n".join(lines)

    lines.append(
        f"- Failed requests: **{summary.failures:,} / {summary.requests:,} "
        f"({summary.error_rate:.4f}%)**"
    )
    lines.append("- Deployments:")
    for deployment in summary.deployments:
        detail = (
            f"{deployment.failures:,} / {deployment.requests:,} "
            f"({deployment.error_rate:.4f}%)"
        )
        if deployment.failure_analysis_link:
            detail += (
                " — "
                f"[open native Failure Analysis]({deployment.failure_analysis_link})"
            )
        lines.append(f"  - `{deployment.service_name}`: {detail}")

    lines.extend(("", "Top failing endpoints/statuses:"))
    if summary.top_errors:
        for index, group in enumerate(summary.top_errors, start=1):
            endpoint = group.endpoint or "(unknown endpoint)"
            status = f" · HTTP {group.http_status}" if group.http_status else ""
            lines.append(
                f"{index}. `{endpoint}`{status} — **{group.failures:,} failures**"
            )
    elif summary.failures == 0:
        lines.append("No failed requests were observed; endpoint ranking was skipped.")
    else:
        lines.append("No failed endpoint groups were returned.")
    lines.extend(
        ("", f"[Open the exact error breakdown in Dynatrace]({summary.breakdown_link})")
    )
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize service failures by deployment, endpoint, and HTTP status."
        )
    )
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--lookback", default="1d")
    parser.add_argument("--end-time", help="Optional RFC 3339 end time for reproduction.")
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help=f"Number of failing endpoint groups to show (1-{MAX_ERROR_GROUPS}).",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        summary = execute_error_summary(
            environment=args.environment,
            service=args.service,
            lookback=args.lookback,
            end_time=args.end_time,
            top=args.top,
        )
    except (RundownError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    print(render_markdown(summary))


if __name__ == "__main__":
    main()
