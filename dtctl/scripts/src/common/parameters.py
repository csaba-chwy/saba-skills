#!/usr/bin/env python3
"""Shared validation, time handling, and CLI arguments for service scripts."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re


ENVIRONMENTS = ("prd", "stg", "qat", "dev")
INTERVAL_RE = re.compile(r"^[1-9][0-9]*(?:ns|us|ms|s|m|h|d|w)$")
LOOKBACK_RE = re.compile(r"^([1-9][0-9]*)(m|h|d|w)$")
SERVICE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_environment(environment: str) -> None:
    if environment not in ENVIRONMENTS:
        raise ValueError(
            f"environment must be one of: {', '.join(ENVIRONMENTS)}"
        )


def validate_service(service: str) -> None:
    if not SERVICE_RE.fullmatch(service):
        raise ValueError("service must be an untagged telemetry stem")


def validate_interval(interval: str) -> None:
    if not INTERVAL_RE.fullmatch(interval):
        raise ValueError(
            "interval must be a positive DQL duration such as 5m or 1h"
        )


def validate_latency_percentile(latency_percentile: int) -> None:
    if not 1 <= latency_percentile <= 99:
        raise ValueError("latency percentile must be between 1 and 99")


def parse_timestamp(value: str, name: str = "end time") -> datetime:
    """Parse one offset-aware RFC 3339 timestamp and normalize it to UTC."""
    if any(character in value for character in ('"', "\n", "\r")):
        raise ValueError(f"{name} must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a UTC offset or Z suffix")
    return parsed.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def parse_duration(value: str, name: str = "lookback") -> timedelta:
    """Parse a bounded-window duration supported by the service runners."""
    match = LOOKBACK_RE.fullmatch(value)
    if match is None:
        raise ValueError(
            f"{name} must be a duration such as 30m, 6h, 1d, or 1w"
        )
    amount = int(match.group(1))
    unit = match.group(2)
    return {
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
        "w": timedelta(weeks=amount),
    }[unit]


def resolve_window(
    lookback: str,
    *,
    end_time: str | None = None,
    now: datetime | None = None,
) -> tuple[str, str]:
    """Resolve a lookback and optional end time to an absolute UTC window."""
    duration = parse_duration(lookback)
    end = (
        parse_timestamp(end_time)
        if end_time
        else (now or datetime.now(timezone.utc))
    )
    end = end.astimezone(timezone.utc).replace(microsecond=0)
    return format_timestamp(end - duration), format_timestamp(end)


def validate_absolute_window(start: str, end: str) -> None:
    """Require a bounded, increasing pair of absolute RFC 3339 timestamps."""
    parsed_start = parse_timestamp(start, "start")
    parsed_end = parse_timestamp(end, "end")
    if parsed_end <= parsed_start:
        raise ValueError("end must be later than start")


def validate_service_window(
    environment: str,
    service: str,
    start: str,
    end: str,
) -> None:
    validate_environment(environment)
    validate_service(service)
    validate_absolute_window(start, end)


def build_service_filter(environment: str, service: str) -> str:
    """Return the standard logical-service DQL filter."""
    return (
        f'startsWith(service.name, "[{environment}]") and '
        f'endsWith(service.name, "]{service}")'
    )


def add_service_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the standard environment and logical-service CLI arguments."""
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--service", required=True)


def add_absolute_window_arguments(
    parser: argparse.ArgumentParser,
    *,
    prefix: str | None = None,
) -> None:
    """Add a required absolute time window, optionally with a name prefix."""
    if prefix:
        parser.add_argument(f"--{prefix}-start", required=True)
        parser.add_argument(f"--{prefix}-end", required=True)
        return
    parser.add_argument("--from-time", dest="start", required=True)
    parser.add_argument("--to-time", dest="end", required=True)


def add_lookback_arguments(
    parser: argparse.ArgumentParser,
    *,
    default: str,
    end_time_help: str = "Optional RFC 3339 end time for reproduction.",
) -> None:
    """Add a relative lookback and optional reproducible end timestamp."""
    parser.add_argument("--lookback", default=default)
    parser.add_argument("--end-time", help=end_time_help)


def add_interval_argument(
    parser: argparse.ArgumentParser,
    *,
    default: str,
) -> None:
    parser.add_argument("--interval", default=default)


def add_latency_percentile_argument(
    parser: argparse.ArgumentParser,
    *,
    default: int = 95,
) -> None:
    parser.add_argument("--latency-percentile", type=int, default=default)


def add_dql_link_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the common environment URL and DQL file link-builder arguments."""
    parser.add_argument("--environment-url", required=True)
    parser.add_argument("--dql-file", required=True, type=Path)
