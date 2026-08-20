#!/usr/bin/env python3
"""Build the standard metric timeline DQL for a service rundown."""

from __future__ import annotations

import argparse
from datetime import datetime
import re


ENVIRONMENTS = ("prd", "stg", "qat", "dev")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
INTERVAL_RE = re.compile(r"^[1-9][0-9]*(?:ns|us|ms|s|m|h|d|w)$")
SERVICE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _validate_identifier(value: str) -> str:
    if not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"invalid DQL grouping field: {value!r}")
    return value


def _validate_additional_filter(value: str) -> str:
    if any(token in value for token in ("\n", "\r", "|", "{", "}", "//", "/*")):
        raise ValueError("additional filters must be one pipeline-free DQL expression")
    if not value.strip():
        raise ValueError("additional filters cannot be empty")
    return value.strip()


def _parse_absolute_timestamp(value: str, name: str) -> datetime:
    if any(char in value for char in ('"', "\n", "\r")):
        raise ValueError(f"{name} must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a UTC offset or Z suffix")
    return parsed


def build_rundown_query(
    *,
    environment: str,
    service: str,
    start: str,
    end: str,
    interval: str = "15m",
    group_by: tuple[str, ...] = (),
    additional_filters: tuple[str, ...] = (),
    latency_percentile: int = 95,
) -> str:
    """Return one plot-ready DQL query for traffic, errors, and latency."""
    if environment not in ENVIRONMENTS:
        raise ValueError(f"environment must be one of: {', '.join(ENVIRONMENTS)}")
    if not SERVICE_RE.fullmatch(service):
        raise ValueError("service must be an untagged telemetry stem")
    parsed_start = _parse_absolute_timestamp(start, "start")
    parsed_end = _parse_absolute_timestamp(end, "end")
    if parsed_end <= parsed_start:
        raise ValueError("end must be later than start")
    if not INTERVAL_RE.fullmatch(interval):
        raise ValueError("interval must be a positive DQL duration such as 5m or 1h")
    if not 1 <= latency_percentile <= 99:
        raise ValueError("latency percentile must be between 1 and 99")

    dimensions = tuple(_validate_identifier(value) for value in group_by)
    extra_filters = tuple(
        _validate_additional_filter(value) for value in additional_filters
    )
    service_filter = (
        f'startsWith(service.name, "[{environment}]") and '
        f'endsWith(service.name, "]{service}")'
    )
    combined_filter = " and ".join((service_filter, *extra_filters))
    by_clause = f", by: {{ {', '.join(dimensions)} }}" if dimensions else ""
    dimension_fields = f", {', '.join(dimensions)}" if dimensions else ""
    percentile_field = f"latency_p{latency_percentile}_us"
    latency_ms_field = f"latency_p{latency_percentile}_ms"

    return "\n".join(
        (
            "timeseries {",
            "  requests = sum(dt.service.request.count),",
            "  failed_requests = sum(dt.service.request.count, "
            "filter: { failed == true }, default: 0),",
            f"  {percentile_field} = percentile("
            f"dt.service.request.response_time, {latency_percentile})",
            f"}}, interval: {interval}{by_clause}, filter: {{ {combined_filter} }}, "
            f'from: "{start}", to: "{end}", nonempty: true',
            "| fieldsAdd error_rate = if(requests[] > 0, "
            "100.0 * failed_requests[] / requests[], else: 0.0), "
            f"{latency_ms_field} = {percentile_field}[] / 1000.0",
            f"| fields timeframe, interval{dimension_fields}, requests, error_rate, "
            f"{latency_ms_field}",
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build plot-ready service rundown DQL for request count, error rate, "
            "and latency percentile over time."
        )
    )
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--from-time", dest="start", required=True)
    parser.add_argument("--to-time", dest="end", required=True)
    parser.add_argument("--interval", default="15m")
    parser.add_argument(
        "--group-by",
        action="append",
        default=[],
        help="Low-cardinality DQL field; repeat to add grouping dimensions.",
    )
    parser.add_argument(
        "--additional-filter",
        action="append",
        default=[],
        help="Pipeline-free DQL expression; repeat to narrow a follow-up.",
    )
    parser.add_argument("--latency-percentile", type=int, default=95)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        build_rundown_query(
            environment=args.environment,
            service=args.service,
            start=args.start,
            end=args.end,
            interval=args.interval,
            group_by=tuple(args.group_by),
            additional_filters=tuple(args.additional_filter),
            latency_percentile=args.latency_percentile,
        )
    )


if __name__ == "__main__":
    main()
