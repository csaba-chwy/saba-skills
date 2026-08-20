#!/usr/bin/env python3
"""Build a Dynatrace Logs and Events Advanced-mode summarized bar-chart URL."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re
from urllib.parse import quote, urlencode

from build_logs_events_link import (
    LOGS_EVENTS_PATH,
    normalize_dql,
    normalize_environment_url,
)


LOGS_EVENTS_GRAPH_PARAMS = (
    ("gtf", "-2h"),
    ("gf", "all"),
    ("advancedQueryMode", "true"),
    ("visualizationType", "barChart"),
    ("isDefaultQuery", "true"),
)


def build_graph_link(environment_url: str, dql: str) -> str:
    normalized_dql = normalize_dql(dql)
    if not normalized_dql.lstrip().startswith("timeseries"):
        raise ValueError("graph DQL must start with a timeseries command")
    if re.search(r"(?im)^\s*\|\s*summarize\b", normalized_dql) is None:
        raise ValueError(
            "graph DQL must summarize timeseries arrays into scalar rows"
        )

    encoded_dql = quote(normalized_dql, safe="")
    fragment = base64.b64encode(encoded_dql.encode("utf-8")).decode("ascii")
    query = urlencode(LOGS_EVENTS_GRAPH_PARAMS)
    return (
        f"{normalize_environment_url(environment_url)}"
        f"{LOGS_EVENTS_PATH}?{query}#{fragment}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a Dynatrace Logs and Events bar-chart link for exact "
            "summarized metric DQL."
        )
    )
    parser.add_argument("--environment-url", required=True)
    parser.add_argument("--dql-file", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        build_graph_link(
            args.environment_url,
            args.dql_file.read_text(encoding="utf-8"),
        )
    )


if __name__ == "__main__":
    main()
