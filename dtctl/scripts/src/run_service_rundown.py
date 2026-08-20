#!/usr/bin/env python3
"""Run one scalar Dynatrace service rundown and print ready-to-send Markdown."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
import re
import subprocess
import sys
from typing import Callable, Mapping, Sequence

from build_logs_events_link import build_link, normalize_environment_url
from build_service_rundown_query import (
    ENVIRONMENTS,
    build_scalar_rundown_query,
)


DURATION_RE = re.compile(r"^([1-9][0-9]*)(m|h|d|w)$")
CONTEXTS = {
    "prd": ("prod", "DTCTL_PROD_ENVIRONMENT"),
    "stg": ("nonprod", "DTCTL_NONPROD_ENVIRONMENT"),
    "qat": ("nonprod", "DTCTL_NONPROD_ENVIRONMENT"),
    "dev": ("nonprod", "DTCTL_NONPROD_ENVIRONMENT"),
}
CommandRunner = Callable[[Sequence[str], int], subprocess.CompletedProcess[str]]


class RundownError(RuntimeError):
    """Raised when a safe rundown cannot be completed."""


@dataclass(frozen=True)
class Rundown:
    environment: str
    service: str
    context: str
    start: str
    end: str
    lookback: str
    requests: int
    failed_requests: int
    error_rate: float
    latency_p95_ms: float
    link: str


def _run(command: Sequence[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise RundownError("dtctl is not installed or is not on PATH") from error
    except subprocess.TimeoutExpired as error:
        raise RundownError(f"command timed out after {timeout} seconds") from error


def parse_duration(value: str) -> timedelta:
    match = DURATION_RE.fullmatch(value)
    if match is None:
        raise ValueError("lookback must be a duration such as 30m, 6h, 1d, or 1w")
    amount = int(match.group(1))
    unit = match.group(2)
    return {
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
        "w": timedelta(weeks=amount),
    }[unit]


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("end time must be an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError("end time must include a UTC offset or Z suffix")
    return parsed.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def resolve_window(
    lookback: str,
    *,
    end_time: str | None = None,
    now: datetime | None = None,
) -> tuple[str, str]:
    duration = parse_duration(lookback)
    end = parse_timestamp(end_time) if end_time else (now or datetime.now(timezone.utc))
    end = end.astimezone(timezone.utc).replace(microsecond=0)
    return format_timestamp(end - duration), format_timestamp(end)


def _field(output: str, name: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(\S.*?)\s*$", output)
    return match.group(1).strip() if match else None


def _login_command(context: str, variable: str) -> str:
    return (
        f'dtctl auth login --context {context} --environment "${variable}" '
        "--safety-level readonly"
    )


def verify_context(
    environment: str,
    *,
    environ: Mapping[str, str],
    runner: CommandRunner,
) -> tuple[str, str]:
    context, variable = CONTEXTS[environment]
    configured_url = environ.get(variable, "")
    try:
        expected_url = normalize_environment_url(configured_url)
    except ValueError as error:
        raise RundownError(f"{variable} must contain the target https URL") from error

    describe = runner(
        ["dtctl", "config", "describe-context", context, "--plain"], 15
    )
    observed_url = _field(describe.stdout, "Environment")
    safety_level = _field(describe.stdout, "Safety Level")
    if describe.returncode != 0 or observed_url is None:
        raise RundownError(
            f"{context} context is unavailable; run: "
            f"{_login_command(context, variable)}"
        )
    try:
        normalized_observed_url = normalize_environment_url(observed_url)
    except ValueError as error:
        raise RundownError(
            f"{context} context has an invalid environment URL"
        ) from error
    if normalized_observed_url != expected_url:
        raise RundownError(f"{context} context does not match {variable}")
    if safety_level != "readonly":
        raise RundownError(f"{context} context must use safety level readonly")

    auth = runner(["dtctl", "--context", context, "auth", "status", "--plain"], 15)
    access_token = _field(auth.stdout, "Access token") or ""
    refresh_token = _field(auth.stdout, "Refresh token")
    reusable_session = access_token.startswith("valid for") or refresh_token == "present"
    if (
        auth.returncode != 0
        or _field(auth.stdout, "Auth type") != "OAuth"
        or not reusable_session
    ):
        raise RundownError(
            f"{context} OAuth session is unavailable; run: "
            f"{_login_command(context, variable)}"
        )
    return context, expected_url


def _number(record: Mapping[str, object], name: str) -> float:
    value = record.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RundownError(f"Dynatrace result is missing numeric field {name}")
    return float(value)


def execute_rundown(
    *,
    environment: str,
    service: str,
    lookback: str = "1d",
    end_time: str | None = None,
    environ: Mapping[str, str] | None = None,
    runner: CommandRunner = _run,
    now: datetime | None = None,
) -> Rundown:
    start, end = resolve_window(lookback, end_time=end_time, now=now)
    context, environment_url = verify_context(
        environment,
        environ=environ if environ is not None else os.environ,
        runner=runner,
    )
    dql = build_scalar_rundown_query(
        environment=environment,
        service=service,
        start=start,
        end=end,
    )
    result = runner(
        [
            "dtctl",
            "--context",
            context,
            "query",
            dql,
            "--fetch-timeout-seconds",
            "60",
            "-o",
            "json",
            "--plain",
        ],
        70,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "query failed"
        raise RundownError(detail)
    try:
        records = json.loads(result.stdout).get("records", [])
    except (json.JSONDecodeError, AttributeError) as error:
        raise RundownError("dtctl returned invalid JSON") from error
    if len(records) != 1 or not isinstance(records[0], dict):
        raise RundownError("Dynatrace returned no scalar service metrics")
    record = records[0]
    return Rundown(
        environment=environment,
        service=service,
        context=context,
        start=start,
        end=end,
        lookback=lookback,
        requests=round(_number(record, "requests")),
        failed_requests=round(_number(record, "failed_requests")),
        error_rate=_number(record, "error_rate"),
        latency_p95_ms=_number(record, "latency_p95_ms"),
        link=build_link(environment_url, dql),
    )


def render_markdown(result: Rundown) -> str:
    return "\n".join(
        (
            f"### `[{result.environment}]{result.service}` — last {result.lookback}",
            f"`{result.context}` · `{result.start}` to `{result.end}`",
            "",
            f"- Requests: **{result.requests:,}**",
            f"- Failed requests: **{result.failed_requests:,}**",
            f"- Error rate: **{result.error_rate:.4f}%**",
            f"- p95 latency: **{result.latency_p95_ms:.2f} ms**",
            "",
            f"[Open the exact query in Dynatrace]({result.link})",
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one scalar request/error/latency rundown and print Markdown."
    )
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--lookback", default="1d")
    parser.add_argument("--end-time", help="Optional RFC 3339 end time for reproduction.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = execute_rundown(
            environment=args.environment,
            service=args.service,
            lookback=args.lookback,
            end_time=args.end_time,
        )
    except (RundownError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    print(render_markdown(result))


if __name__ == "__main__":
    main()
