#!/usr/bin/env python3
"""Build a tenant-correct Dynatrace Logs and Events Advanced-mode DQL URL."""

from __future__ import annotations

import argparse
import base64
from urllib.parse import quote, urlencode

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.parameters import add_dql_link_arguments
from links.common import normalize_dql, normalize_environment_url


LOGS_EVENTS_PATH = "/ui/apps/dynatrace.classic.logs.events/ui/logs-events"
LOGS_EVENTS_PARAMS = (
    ("gtf", "-2h"),
    ("gf", "all"),
    ("sortDirection", "desc"),
    ("visibleColumns", "timestamp"),
    ("visibleColumns", "status"),
    ("visibleColumns", "content"),
    ("advancedQueryMode", "true"),
    ("visualizationType", "table"),
    ("isDefaultQuery", "true"),
)


def build_link(environment_url: str, dql: str) -> str:
    encoded_dql = quote(normalize_dql(dql), safe="")
    fragment = base64.b64encode(encoded_dql.encode("utf-8")).decode("ascii")
    query = urlencode(LOGS_EVENTS_PARAMS)
    return f"{normalize_environment_url(environment_url)}{LOGS_EVENTS_PATH}?{query}#{fragment}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Dynatrace Logs and Events Advanced-mode link for exact DQL."
    )
    add_dql_link_arguments(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(build_link(args.environment_url, args.dql_file.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
