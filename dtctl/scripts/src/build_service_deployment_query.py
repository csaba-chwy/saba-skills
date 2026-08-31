#!/usr/bin/env python3
"""Build request-count DQL that locates traffic for one deployed version."""

from __future__ import annotations

import argparse
import re

from build_service_rundown_query import (
    ENVIRONMENTS,
    INTERVAL_RE,
    build_service_filter,
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
    if not INTERVAL_RE.fullmatch(interval):
        raise ValueError("interval must be a positive duration such as 1m, 5m, or 1h")
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
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--from-time", dest="start", required=True)
    parser.add_argument("--to-time", dest="end", required=True)
    parser.add_argument("--interval", default="5m")
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
