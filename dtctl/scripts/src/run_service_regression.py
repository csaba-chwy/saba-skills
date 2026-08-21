#!/usr/bin/env python3
"""Compare service RED metrics around a known deployment or change time."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import sys
from typing import Mapping, Sequence

from build_logs_events_link import build_link
from build_service_regression_query import build_service_regression_query
from build_service_rundown_query import ENVIRONMENTS
from run_service_rundown import (
    CommandRunner,
    RundownError,
    _run,
    format_timestamp,
    parse_duration,
    parse_timestamp,
    query_records,
    verify_context,
)


@dataclass(frozen=True)
class ComparisonWindows:
    change_time: str
    before_start: str
    before_end: str
    after_start: str
    after_end: str


@dataclass(frozen=True)
class WindowMetrics:
    requests: int | None
    failures: int | None
    error_rate: float | None
    latency_ms: float | None


@dataclass(frozen=True)
class RegressionSummary:
    environment: str
    service: str
    context: str
    windows: ComparisonWindows
    latency_percentile: int
    before: WindowMetrics
    after: WindowMetrics
    latency_change_pct: float | None
    error_rate_change_pp: float | None
    request_change_pct: float | None
    reasons: tuple[str, ...]
    link: str

    @property
    def regression_detected(self) -> bool:
        return bool(self.reasons)

    @property
    def insufficient_data(self) -> bool:
        return self.before.requests is None or self.after.requests is None


def resolve_comparison_windows(
    change_time: str,
    *,
    window: str = "30m",
    guard: str = "5m",
) -> ComparisonWindows:
    boundary = parse_timestamp(change_time)
    window_delta = parse_duration(window)
    guard_delta = parse_duration(guard)
    if guard_delta >= window_delta:
        raise ValueError("guard must be shorter than the comparison window")
    before_end = boundary - guard_delta
    before_start = before_end - window_delta
    after_start = boundary + guard_delta
    after_end = after_start + window_delta
    return ComparisonWindows(
        change_time=format_timestamp(boundary),
        before_start=format_timestamp(before_start),
        before_end=format_timestamp(before_end),
        after_start=format_timestamp(after_start),
        after_end=format_timestamp(after_end),
    )


def _optional_number(record: Mapping[str, object], name: str) -> float | None:
    value = record.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RundownError(f"Dynatrace result has invalid numeric field {name}")
    return float(value)


def _optional_integer(record: Mapping[str, object], name: str) -> int | None:
    value = _optional_number(record, name)
    return round(value) if value is not None else None


def _metrics(
    records: Sequence[Mapping[str, object]],
    *,
    label: str,
    latency_percentile: int,
) -> WindowMetrics:
    matches = [record for record in records if record.get("comparison_window") == label]
    if len(matches) != 1:
        raise RundownError(f"Dynatrace returned no unique {label} comparison row")
    record = matches[0]
    requests = _optional_integer(record, "requests")
    failures = _optional_integer(record, "failed_requests")
    return WindowMetrics(
        requests=requests,
        failures=failures,
        error_rate=(
            100.0 * failures / requests
            if requests is not None and requests > 0 and failures is not None
            else None
        ),
        latency_ms=_optional_number(record, f"latency_p{latency_percentile}_ms"),
    )


def _percent_change(before: float, after: float) -> float | None:
    return 100.0 * (after - before) / before if before else None


def execute_regression_check(
    *,
    environment: str,
    service: str,
    change_time: str,
    window: str = "30m",
    guard: str = "5m",
    latency_percentile: int = 95,
    latency_increase_pct: float = 20.0,
    latency_absolute_ms: float = 2000.0,
    error_rate_increase_pp: float = 1.0,
    request_drop_pct: float = 20.0,
    environ: Mapping[str, str] | None = None,
    runner: CommandRunner = _run,
) -> RegressionSummary:
    for name, value in (
        ("latency increase", latency_increase_pct),
        ("absolute latency", latency_absolute_ms),
        ("error-rate increase", error_rate_increase_pp),
        ("request drop", request_drop_pct),
    ):
        if value < 0:
            raise ValueError(f"{name} threshold cannot be negative")
    if not 1 <= latency_percentile <= 99:
        raise ValueError("latency percentile must be between 1 and 99")

    windows = resolve_comparison_windows(change_time, window=window, guard=guard)
    context, environment_url = verify_context(
        environment,
        environ=environ if environ is not None else os.environ,
        runner=runner,
    )
    dql = build_service_regression_query(
        environment=environment,
        service=service,
        before_start=windows.before_start,
        before_end=windows.before_end,
        after_start=windows.after_start,
        after_end=windows.after_end,
        latency_percentile=latency_percentile,
    )
    records = query_records(runner, context, dql)
    before = _metrics(records, label="before", latency_percentile=latency_percentile)
    after = _metrics(records, label="after", latency_percentile=latency_percentile)
    latency_change = (
        _percent_change(before.latency_ms, after.latency_ms)
        if before.latency_ms is not None and after.latency_ms is not None
        else None
    )
    error_rate_change = (
        after.error_rate - before.error_rate
        if before.error_rate is not None and after.error_rate is not None
        else None
    )
    request_change = (
        _percent_change(before.requests, after.requests)
        if before.requests is not None and after.requests is not None
        else None
    )

    reasons = []
    if latency_change is not None and latency_change > latency_increase_pct:
        reasons.append(f"p{latency_percentile} latency increased {latency_change:.1f}%")
    if after.latency_ms is not None and after.latency_ms > latency_absolute_ms:
        reasons.append(
            f"p{latency_percentile} latency reached {after.latency_ms:.1f} ms"
        )
    if error_rate_change is not None and error_rate_change > error_rate_increase_pp:
        reasons.append(
            f"error rate increased {error_rate_change:.2f} percentage points"
        )
    if request_change is not None and request_change < -request_drop_pct:
        reasons.append(f"request volume dropped {-request_change:.1f}%")

    return RegressionSummary(
        environment=environment,
        service=service,
        context=context,
        windows=windows,
        latency_percentile=latency_percentile,
        before=before,
        after=after,
        latency_change_pct=latency_change,
        error_rate_change_pp=error_rate_change,
        request_change_pct=request_change,
        reasons=tuple(reasons),
        link=build_link(environment_url, dql),
    )


def _change(value: float | None, suffix: str = "%") -> str:
    return "unavailable" if value is None else f"{value:+.2f}{suffix}"


def _count(value: int | None) -> str:
    return "unavailable" if value is None else f"{value:,}"


def _rate(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.4f}%"


def render_markdown(summary: RegressionSummary) -> str:
    if summary.insufficient_data:
        outcome = "Insufficient data"
    elif summary.regression_detected:
        outcome = "Regression detected"
    else:
        outcome = "No regression detected"
    p = summary.latency_percentile
    before_latency = (
        "unavailable"
        if summary.before.latency_ms is None
        else f"{summary.before.latency_ms:.2f} ms"
    )
    after_latency = (
        "unavailable"
        if summary.after.latency_ms is None
        else f"{summary.after.latency_ms:.2f} ms"
    )
    lines = [
        f"### {outcome}: `[{summary.environment}]{summary.service}`",
        f"`{summary.context}` · change boundary `{summary.windows.change_time}`",
        "",
        f"- Before: `{summary.windows.before_start}` to `{summary.windows.before_end}`",
        f"- After: `{summary.windows.after_start}` to `{summary.windows.after_end}`",
        f"- Requests: **{_count(summary.before.requests)} → "
        f"{_count(summary.after.requests)}** "
        f"({_change(summary.request_change_pct)})",
        f"- Error rate: **{_rate(summary.before.error_rate)} → "
        f"{_rate(summary.after.error_rate)}** "
        f"({_change(summary.error_rate_change_pp, ' pp')})",
        f"- p{p} latency: **{before_latency} → {after_latency}** "
        f"({_change(summary.latency_change_pct)})",
    ]
    if summary.insufficient_data:
        lines.extend(
            (
                "",
                "One or both windows had no request-count data, so no regression "
                "conclusion was made.",
            )
        )
    elif summary.reasons:
        lines.extend(("", "Thresholds exceeded:"))
        lines.extend(f"- {reason}" for reason in summary.reasons)
    else:
        lines.extend(
            (
                "",
                "The comparison stayed within the configured thresholds. Stop here "
                "unless another window or signal was requested.",
            )
        )
    lines.extend(("", f"[Open the exact comparison in Dynatrace]({summary.link})"))
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check one service for a metric regression around a known change."
    )
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--change-time", required=True)
    parser.add_argument("--window", default="30m")
    parser.add_argument("--guard", default="5m")
    parser.add_argument("--latency-percentile", type=int, default=95)
    parser.add_argument("--latency-increase-pct", type=float, default=20.0)
    parser.add_argument("--latency-absolute-ms", type=float, default=2000.0)
    parser.add_argument("--error-rate-increase-pp", type=float, default=1.0)
    parser.add_argument("--request-drop-pct", type=float, default=20.0)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        summary = execute_regression_check(
            environment=args.environment,
            service=args.service,
            change_time=args.change_time,
            window=args.window,
            guard=args.guard,
            latency_percentile=args.latency_percentile,
            latency_increase_pct=args.latency_increase_pct,
            latency_absolute_ms=args.latency_absolute_ms,
            error_rate_increase_pp=args.error_rate_increase_pp,
            request_drop_pct=args.request_drop_pct,
        )
    except (RundownError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    print(render_markdown(summary))


if __name__ == "__main__":
    main()
