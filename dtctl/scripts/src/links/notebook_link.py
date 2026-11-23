#!/usr/bin/env python3
"""Build a tenant-correct Dynatrace Notebooks query intent URL."""

from __future__ import annotations

import argparse
import json
import re
from urllib.parse import quote_plus, urlsplit, urlunsplit

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.parameters import add_dql_link_arguments


NOTEBOOK_QUERY_PATH = "/ui/intent/dynatrace.notebooks/view-query"


def normalize_environment_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("environment URL must be an absolute https URL")
    if parsed.query or parsed.fragment:
        raise ValueError("environment URL must not contain a query or fragment")
    base_path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, base_path, "", ""))


def normalize_dql(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not normalized.strip():
        raise ValueError("DQL file must not be empty")
    for line in normalized.splitlines():
        quote_character: str | None = None
        escaped = False
        for index, character in enumerate(line):
            if escaped:
                escaped = False
                continue
            if character == "\\" and quote_character is not None:
                escaped = True
                continue
            if character in {'"', "'"}:
                if quote_character == character:
                    quote_character = None
                elif quote_character is None:
                    quote_character = character
                continue
            if character == "|" and quote_character is None and line[:index].strip():
                raise ValueError(
                    "put every DQL pipeline command on its own line before linking"
                )
    return normalized


def build_link(
    environment_url: str,
    dql: str,
    *,
    title: str,
    line_chart: bool = False,
) -> str:
    normalized_dql = normalize_dql(dql)
    if line_chart:
        validate_timeseries(normalized_dql)

    # Match dtctl open intent without an app-discovery call for every summary.
    payload = json.dumps(
        {
            "dt.query": normalized_dql,
            "title": title,
            "visualization": "lineChart" if line_chart else "table",
            "visualizationSettings": {"autoSelectVisualization": False},
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return (
        f"{normalize_environment_url(environment_url)}"
        f"{NOTEBOOK_QUERY_PATH}#{quote_plus(payload, safe='')}"
    )


def validate_timeseries(normalized_dql: str) -> None:
    if re.match(r"(?i)\s*timeseries\b", normalized_dql) is None:
        raise ValueError("graph DQL must start with a timeseries command")
    if re.search(r"(?i)\binterval\s*:", normalized_dql) is None:
        raise ValueError("graph DQL must declare an explicit timeseries interval")
    if re.search(r"(?i)\bscalar\s*:\s*true\b", normalized_dql) is not None:
        raise ValueError("graph DQL must preserve native timeseries arrays")
    if re.search(r"(?i)\|\s*summarize\b", normalized_dql) is not None:
        raise ValueError("graph DQL must preserve time buckets, not summarize them")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Dynatrace Notebooks table or line chart link for exact DQL."
    )
    add_dql_link_arguments(parser)
    parser.add_argument("--title", required=True, help="Notebook section title")
    parser.add_argument(
        "--line-chart", action="store_true", help="Display a native timeseries as a line chart"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        build_link(
            args.environment_url,
            args.dql_file.read_text(encoding="utf-8"),
            title=args.title,
            line_chart=args.line_chart,
        )
    )


if __name__ == "__main__":
    main()
