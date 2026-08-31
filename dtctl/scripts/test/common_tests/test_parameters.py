import argparse
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from common.parameters import (
    add_absolute_window_arguments,
    add_dql_link_arguments,
    add_interval_argument,
    add_lookback_arguments,
    add_service_arguments,
    build_service_filter,
    resolve_window,
    validate_interval,
    validate_service_window,
)


class CommonParametersTest(unittest.TestCase):
    def test_resolves_lookback_to_absolute_utc_window(self) -> None:
        start, end = resolve_window(
            "1d",
            now=datetime(2026, 8, 20, 22, 24, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(start, "2026-08-19T22:24:02Z")
        self.assertEqual(end, "2026-08-20T22:24:02Z")

    def test_validates_service_scope_and_absolute_window_together(self) -> None:
        validate_service_window(
            "prd",
            "sf-item",
            "2026-08-20T21:00:00Z",
            "2026-08-20T22:00:00Z",
        )

        with self.assertRaisesRegex(ValueError, "untagged telemetry stem"):
            validate_service_window(
                "prd",
                "[prd]sf-item",
                "2026-08-20T21:00:00Z",
                "2026-08-20T22:00:00Z",
            )

    def test_builds_the_standard_service_name_filter(self) -> None:
        self.assertEqual(
            build_service_filter("prd", "sf-item"),
            'startsWith(service.name, "[prd]") and '
            'endsWith(service.name, "]sf-item")',
        )

    def test_rejects_relative_or_zero_intervals(self) -> None:
        for interval in ("0m", "-5m", "yesterday"):
            with self.subTest(interval=interval):
                with self.assertRaisesRegex(ValueError, "positive DQL duration"):
                    validate_interval(interval)

    def test_adds_consistent_service_window_arguments(self) -> None:
        parser = argparse.ArgumentParser()
        add_service_arguments(parser)
        add_lookback_arguments(parser, default="14d")
        add_interval_argument(parser, default="5m")

        args = parser.parse_args(
            ["--environment", "prd", "--service", "sf-item"]
        )

        self.assertEqual(args.environment, "prd")
        self.assertEqual(args.service, "sf-item")
        self.assertEqual(args.lookback, "14d")
        self.assertIsNone(args.end_time)
        self.assertEqual(args.interval, "5m")

    def test_adds_prefixed_absolute_windows(self) -> None:
        parser = argparse.ArgumentParser()
        add_absolute_window_arguments(parser, prefix="before")

        args = parser.parse_args(
            [
                "--before-start",
                "2026-08-20T21:00:00Z",
                "--before-end",
                "2026-08-20T22:00:00Z",
            ]
        )

        self.assertEqual(args.before_start, "2026-08-20T21:00:00Z")
        self.assertEqual(args.before_end, "2026-08-20T22:00:00Z")

    def test_adds_consistent_link_builder_arguments(self) -> None:
        parser = argparse.ArgumentParser()
        add_dql_link_arguments(parser)

        args = parser.parse_args(
            [
                "--environment-url",
                "https://example.com",
                "--dql-file",
                "query.dql",
            ]
        )

        self.assertEqual(args.environment_url, "https://example.com")
        self.assertEqual(args.dql_file, Path("query.dql"))


if __name__ == "__main__":
    unittest.main()
