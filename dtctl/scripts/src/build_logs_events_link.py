#!/usr/bin/env python3
"""Build a tenant-correct Dynatrace Logs and Events Advanced-mode DQL URL."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit, urlunsplit


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


def build_link(environment_url: str, dql: str) -> str:
    encoded_dql = quote(normalize_dql(dql), safe="")
    fragment = base64.b64encode(encoded_dql.encode("utf-8")).decode("ascii")
    query = urlencode(LOGS_EVENTS_PARAMS)
    return f"{normalize_environment_url(environment_url)}{LOGS_EVENTS_PATH}?{query}#{fragment}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Dynatrace Logs and Events Advanced-mode link for exact DQL."
    )
    parser.add_argument("--environment-url", required=True)
    parser.add_argument("--dql-file", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(build_link(args.environment_url, args.dql_file.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
