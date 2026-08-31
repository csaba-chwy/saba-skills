#!/usr/bin/env python3
"""Build standard metric DQL for service rundowns."""

from __future__ import annotations

import argparse
import re

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.parameters import (
    add_absolute_window_arguments,
    add_interval_argument,
    add_latency_percentile_argument,
    add_service_arguments,
    build_service_filter,
    validate_interval,
    validate_latency_percentile,
    validate_service_window,
)

RUNDOWN_METRICS = ("requests", "failures", "error-rate", "latency")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
ENTITY_ID_RE = re.compile(r"^SERVICE-[A-F0-9]{16}$")
MAX_ERROR_GROUPS = 20


def normalize_metrics(metrics: tuple[str, ...]) -> tuple[str, ...]:
    selected = metrics or RUNDOWN_METRICS
    invalid = set(selected) - set(RUNDOWN_METRICS)
    if invalid:
        raise ValueError(
            "metrics must be selected from: " + ", ".join(RUNDOWN_METRICS)
        )
    return tuple(metric for metric in RUNDOWN_METRICS if metric in selected)


def _metric_parts(
    metrics: tuple[str, ...],
    *,
    latency_percentile: int,
    scalar: bool,
) -> tuple[list[str], list[str], list[str]]:
    selected = normalize_metrics(metrics)
    scalar_option = ", scalar: true" if scalar else ""
    array_suffix = "" if scalar else "[]"
    expressions: list[str] = []
    derived: list[str] = []
    fields: list[str] = []

    if "requests" in selected or "error-rate" in selected:
        expressions.append(
            f"requests = sum(dt.service.request.count{scalar_option})"
        )
    if "failures" in selected or "error-rate" in selected:
        expressions.append(
            "failed_requests = sum(dt.service.request.count, "
            f"filter: {{ failed == true }}, default: 0{scalar_option})"
        )
    if "latency" in selected:
        expressions.append(
            f"latency_p{latency_percentile}_us = percentile("
            "dt.service.request.response_time, "
            f"{latency_percentile}{scalar_option})"
        )

    if "error-rate" in selected:
        derived.append(
            f"error_rate = if(requests{array_suffix} > 0, "
            f"100.0 * failed_requests{array_suffix} / requests{array_suffix}, "
            "else: 0.0)"
        )
    if "latency" in selected:
        derived.append(
            f"latency_p{latency_percentile}_ms = "
            f"latency_p{latency_percentile}_us{array_suffix} / 1000.0"
        )

    output_names = {
        "requests": "requests",
        "failures": "failed_requests",
        "error-rate": "error_rate",
        "latency": f"latency_p{latency_percentile}_ms",
    }
    fields.extend(output_names[metric] for metric in selected)
    return expressions, derived, fields


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
    metrics: tuple[str, ...] = (),
) -> str:
    """Return one link-ready metric timeline for the requested measures."""
    validate_service_window(environment, service, start, end)
    validate_interval(interval)
    validate_latency_percentile(latency_percentile)

    dimensions = tuple(_validate_identifier(value) for value in group_by)
    extra_filters = tuple(
        _validate_additional_filter(value) for value in additional_filters
    )
    service_filter = build_service_filter(environment, service)
    combined_filter = " and ".join((service_filter, *extra_filters))
    by_clause = f", by: {{ {', '.join(dimensions)} }}" if dimensions else ""
    dimension_fields = f", {', '.join(dimensions)}" if dimensions else ""
    expressions, derived, fields = _metric_parts(
        metrics, latency_percentile=latency_percentile, scalar=False
    )
    lines = ["timeseries {"]
    lines.extend(
        f"  {expression}{',' if index < len(expressions) - 1 else ''}"
        for index, expression in enumerate(expressions)
    )
    lines.append(
        f"}}, interval: {interval}{by_clause}, filter: {{ {combined_filter} }}, "
        f'from: "{start}", to: "{end}", nonempty: true'
    )
    if derived:
        lines.append("| fieldsAdd " + ", ".join(derived))
    lines.append(
        f"| fields timeframe, interval{dimension_fields}, {', '.join(fields)}"
    )
    return "\n".join(lines)


def build_scalar_rundown_query(
    *,
    environment: str,
    service: str,
    start: str,
    end: str,
    latency_percentile: int = 95,
    metrics: tuple[str, ...] = (),
) -> str:
    """Return one scalar DQL query for the requested service measures."""
    validate_service_window(environment, service, start, end)
    validate_latency_percentile(latency_percentile)

    service_filter = build_service_filter(environment, service)
    expressions, derived, fields = _metric_parts(
        metrics, latency_percentile=latency_percentile, scalar=True
    )
    selected = normalize_metrics(metrics)
    if (
        ("failures" in selected or "error-rate" in selected)
        and "requests" not in selected
    ):
        if "error-rate" in selected:
            derived.append("metric_presence = requests")
        else:
            expressions.append(
                "metric_presence = sum(dt.service.request.count, scalar: true)"
            )
        fields.append("metric_presence")
    lines = ["timeseries {"]
    lines.extend(
        f"  {expression}{',' if index < len(expressions) - 1 else ''}"
        for index, expression in enumerate(expressions)
    )
    lines.append(
        f"}}, filter: {{ {service_filter} }}, "
        f'from: "{start}", to: "{end}", nonempty: true'
    )
    if derived:
        lines.append("| fieldsAdd " + ", ".join(derived))
    lines.append(f"| fields {', '.join(fields)}")
    return "\n".join(lines)


def build_service_error_totals_query(
    *,
    environment: str,
    service: str,
    start: str,
    end: str,
    entity_ids: tuple[str, ...] = (),
) -> str:
    """Return request totals split by service entity and native failed dimension."""
    validate_service_window(environment, service, start, end)
    service_filter = build_service_selector(environment, service, entity_ids)
    return "\n".join(
        (
            "timeseries requests = sum(dt.service.request.count, scalar: true), "
            "by: { service.name, dt.entity.service, failed }, "
            f"filter: {{ {service_filter} }}, "
            f'from: "{start}", to: "{end}", nonempty: true',
            "| fields service.name, dt.entity.service, failed, requests",
            "| sort service.name asc, failed desc",
            f"| limit {2 * MAX_ERROR_GROUPS}",
        )
    )


def build_top_service_errors_query(
    *,
    environment: str,
    service: str,
    start: str,
    end: str,
    limit: int = 5,
    entity_ids: tuple[str, ...] = (),
) -> str:
    """Return the top failed-request endpoint and HTTP-status groups."""
    validate_service_window(environment, service, start, end)
    if not 1 <= limit <= MAX_ERROR_GROUPS:
        raise ValueError(f"limit must be between 1 and {MAX_ERROR_GROUPS}")
    service_filter = build_service_selector(environment, service, entity_ids)
    return "\n".join(
        (
            "timeseries failures = sum(dt.service.request.count, "
            "filter: { failed == true }, default: 0, scalar: true), "
            "by: { endpoint.name, http.response.status_code }, "
            f"filter: {{ {service_filter} }}, "
            f'from: "{start}", to: "{end}", nonempty: true',
            "| fields endpoint.name, http.response.status_code, failures",
            "| filter failures > 0",
            "| sort failures desc, endpoint.name asc",
            f"| limit {limit}",
        )
    )


def build_service_selector(
    environment: str, service: str, entity_ids: tuple[str, ...]
) -> str:
    """Prefer discovered entity IDs when tagged service.name is unavailable."""
    if not entity_ids:
        return build_service_filter(environment, service)
    invalid = tuple(
        entity_id
        for entity_id in entity_ids
        if not ENTITY_ID_RE.fullmatch(entity_id)
    )
    if invalid:
        raise ValueError("entity IDs must be Dynatrace SERVICE IDs")
    return " or ".join(
        f'dt.entity.service == "{entity_id}"' for entity_id in dict.fromkeys(entity_ids)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build link-ready service rundown DQL for request count, error rate, "
            "and latency percentile over time."
        )
    )
    add_service_arguments(parser)
    add_absolute_window_arguments(parser)
    add_interval_argument(parser, default="15m")
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
    add_latency_percentile_argument(parser)
    parser.add_argument(
        "--metric",
        action="append",
        choices=RUNDOWN_METRICS,
        default=[],
        help="Metric to include; repeat as needed. Defaults to all four.",
    )
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
            metrics=tuple(args.metric),
        )
    )


if __name__ == "__main__":
    main()
