#!/usr/bin/env python3
"""Find first observed request traffic for one deployed service version."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import timedelta
import os
import sys
from typing import Mapping, Sequence

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.parameters import (
    add_interval_argument,
    add_lookback_arguments,
    add_service_arguments,
    format_timestamp,
    parse_timestamp,
    resolve_window,
)
from links.logs_events_graph_link import build_graph_link
from queries.service_deployment import build_service_deployment_query
from runners.service_rundown import (
    CommandRunner,
    RundownError,
    _run,
    query_records,
    verify_context,
)


@dataclass(frozen=True)
class VersionTraffic:
    service_name: str
    version: str
    first_bucket_start: str
    first_bucket_end: str
    requests: int


@dataclass(frozen=True)
class DeploymentSummary:
    environment: str
    service: str
    version: str
    context: str
    start: str
    end: str
    lookback: str
    interval: str
    observations: tuple[VersionTraffic, ...]
    link: str


def _interval_delta(value: object) -> timedelta:
    if isinstance(value, bool):
        raise RundownError("Dynatrace result has invalid timeseries interval")
    try:
        nanoseconds = int(value)  # dtctl JSON represents the interval as nanoseconds.
    except (TypeError, ValueError) as error:
        raise RundownError("Dynatrace result has invalid timeseries interval") from error
    if nanoseconds <= 0:
        raise RundownError("Dynatrace result has invalid timeseries interval")
    return timedelta(microseconds=nanoseconds / 1000)


def _observations_from_records(
    records: Sequence[Mapping[str, object]], *, expected_version: str
) -> tuple[VersionTraffic, ...]:
    observations = []
    for record in records:
        service_name = record.get("service.name")
        version = record.get("primary_tags.version")
        timeframe = record.get("timeframe")
        values = record.get("requests")
        if not isinstance(service_name, str) or not service_name:
            raise RundownError("Dynatrace result is missing service.name")
        if version != expected_version:
            raise RundownError("Dynatrace returned an unexpected version series")
        if not isinstance(timeframe, dict) or not isinstance(
            timeframe.get("start"), str
        ):
            raise RundownError("Dynatrace result is missing its timeseries timeframe")
        if not isinstance(values, list):
            raise RundownError("Dynatrace result is missing its request-count series")

        populated: list[tuple[int, float]] = []
        for index, value in enumerate(values):
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise RundownError("Dynatrace request-count series is not numeric")
            if value > 0:
                populated.append((index, float(value)))
        if not populated:
            continue

        interval = _interval_delta(record.get("interval"))
        series_start = parse_timestamp(timeframe["start"])
        first_index = populated[0][0]
        first_start = series_start + first_index * interval
        observations.append(
            VersionTraffic(
                service_name=service_name,
                version=version,
                first_bucket_start=format_timestamp(first_start),
                first_bucket_end=format_timestamp(first_start + interval),
                requests=round(sum(value for _, value in populated)),
            )
        )
    return tuple(sorted(observations, key=lambda item: item.service_name))


def execute_deployment_summary(
    *,
    environment: str,
    service: str,
    version: str,
    lookback: str = "14d",
    end_time: str | None = None,
    interval: str = "5m",
    environ: Mapping[str, str] | None = None,
    runner: CommandRunner = _run,
) -> DeploymentSummary:
    start, end = resolve_window(lookback, end_time=end_time)
    context, environment_url = verify_context(
        environment,
        environ=environ if environ is not None else os.environ,
        runner=runner,
    )
    dql = build_service_deployment_query(
        environment=environment,
        service=service,
        version=version,
        start=start,
        end=end,
        interval=interval,
    )
    observations = _observations_from_records(
        query_records(runner, context, dql), expected_version=version
    )
    return DeploymentSummary(
        environment=environment,
        service=service,
        version=version,
        context=context,
        start=start,
        end=end,
        lookback=lookback,
        interval=interval,
        observations=observations,
        link=build_graph_link(environment_url, dql),
    )


def render_markdown(summary: DeploymentSummary) -> str:
    lines = [
        f"### Observed version traffic: `[{summary.environment}]{summary.service}` "
        f"`{summary.version}`",
        f"`{summary.context}` · `{summary.start}` to `{summary.end}`",
        "",
    ]
    if not summary.observations:
        lines.extend(
            (
                "No request-count series matched this exact service and "
                "`primary_tags.version` value in the requested window. This does "
                "not prove that the artifact, deployment, or workload does not exist.",
                "",
            )
        )
    else:
        lines.append(
            "First request bucket by regional service (use this as the observed "
            "traffic rollout boundary):"
        )
        for observation in summary.observations:
            lines.append(
                f"- `{observation.service_name}`: `{observation.first_bucket_start}` "
                f"to `{observation.first_bucket_end}`; "
                f"**{observation.requests:,}** requests in the queried window"
            )
        lines.extend(
            (
                "",
                f"Precision is `{summary.interval}`. This is first observed service "
                "traffic for the version, not the image publish time or an exact pod "
                "start time. Treat different regional boundaries separately.",
                "",
            )
        )
    lines.append(f"[Open the exact version timeline in Dynatrace]({summary.link})")
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Locate first request traffic for an exact Service Version."
        )
    )
    add_service_arguments(parser)
    parser.add_argument("--version", required=True)
    add_lookback_arguments(parser, default="14d")
    add_interval_argument(parser, default="5m")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        summary = execute_deployment_summary(
            environment=args.environment,
            service=args.service,
            version=args.version,
            lookback=args.lookback,
            end_time=args.end_time,
            interval=args.interval,
        )
    except (RundownError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    print(render_markdown(summary))


if __name__ == "__main__":
    main()
