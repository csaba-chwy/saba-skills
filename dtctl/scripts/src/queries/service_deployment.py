#!/usr/bin/env python3
"""Build request-count DQL that locates traffic for one deployed version."""

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
    add_service_arguments,
    build_service_filter,
    validate_interval,
    validate_service_window,
)


VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")


def build_service_deployment_query(
    *,
    environment: str,
    service: str,
    version: str,
    start: str,
    end: str,
    interval: str = "5m",
) -> str:
    """Return a version-filtered request timeline grouped by regional service."""
    validate_service_window(environment, service, start, end)
    if not VERSION_RE.fullmatch(version):
        raise ValueError(
            "version must be an exact tag value using letters, digits, dots, "
            "underscores, plus signs, or hyphens"
        )
    validate_interval(interval)
    service_filter = build_service_filter(environment, service)
    return "\n".join(
        (
            "timeseries requests = sum(dt.service.request.count), "
            f"interval: {interval}, "
            "by: { service.name, primary_tags.version }, "
            f"filter: {{ {service_filter} and "
            f'primary_tags.version == "{version}" }}, '
            f'from: "{start}", to: "{end}", nonempty: true',
            "| fields timeframe, interval, service.name, "
            "primary_tags.version, requests",
            "| sort service.name asc",
            "| limit 20",
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build one request-count timeline for an exact Service Version."
        )
    )
    add_service_arguments(parser)
    parser.add_argument("--version", required=True)
    add_absolute_window_arguments(parser)
    add_interval_argument(parser, default="5m")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        build_service_deployment_query(
            environment=args.environment,
            service=args.service,
            version=args.version,
            start=args.start,
            end=args.end,
            interval=args.interval,
        )
    )


if __name__ == "__main__":
    main()
