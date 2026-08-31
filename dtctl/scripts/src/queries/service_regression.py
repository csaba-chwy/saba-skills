#!/usr/bin/env python3
"""Build one DQL query that compares service metrics around a change."""

from __future__ import annotations

import argparse

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.parameters import (
    add_absolute_window_arguments,
    add_latency_percentile_argument,
    add_service_arguments,
    build_service_filter,
    validate_latency_percentile,
    validate_service_window,
)


def _window_query(
    *,
    label: str,
    service_filter: str,
    start: str,
    end: str,
    latency_percentile: int,
) -> list[str]:
    return [
        "timeseries {",
        "  requests = sum(dt.service.request.count, scalar: true),",
        "  failed_requests = sum(dt.service.request.count, "
        "filter: { failed == true }, default: 0, scalar: true),",
        f"  latency_p{latency_percentile}_us = percentile("
        "dt.service.request.response_time, "
        f"{latency_percentile}, scalar: true)",
        f"}}, filter: {{ {service_filter} }}, "
        f'from: "{start}", to: "{end}", nonempty: true',
        f'| fieldsAdd comparison_window = "{label}", '
        f"latency_p{latency_percentile}_ms = "
        f"latency_p{latency_percentile}_us / 1000.0",
        "| fields comparison_window, requests, failed_requests, "
        f"latency_p{latency_percentile}_ms",
    ]


def build_service_regression_query(
    *,
    environment: str,
    service: str,
    before_start: str,
    before_end: str,
    after_start: str,
    after_end: str,
    latency_percentile: int = 95,
) -> str:
    """Return a single two-record before/after service comparison query."""
    validate_service_window(environment, service, before_start, before_end)
    validate_service_window(environment, service, after_start, after_end)
    validate_latency_percentile(latency_percentile)
    service_filter = build_service_filter(environment, service)
    before = _window_query(
        label="before",
        service_filter=service_filter,
        start=before_start,
        end=before_end,
        latency_percentile=latency_percentile,
    )
    after = _window_query(
        label="after",
        service_filter=service_filter,
        start=after_start,
        end=after_end,
        latency_percentile=latency_percentile,
    )
    return "\n".join((*before, "| append [", *(f"  {line}" for line in after), "]"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build one DQL query for a before/after service comparison."
    )
    add_service_arguments(parser)
    add_absolute_window_arguments(parser, prefix="before")
    add_absolute_window_arguments(parser, prefix="after")
    add_latency_percentile_argument(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        build_service_regression_query(
            environment=args.environment,
            service=args.service,
            before_start=args.before_start,
            before_end=args.before_end,
            after_start=args.after_start,
            after_end=args.after_end,
            latency_percentile=args.latency_percentile,
        )
    )


if __name__ == "__main__":
    main()
