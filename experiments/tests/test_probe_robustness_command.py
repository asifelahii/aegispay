import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class RunContextProbeRobustnessCommandTests(SimpleTestCase):
    def test_command_exports_run_and_aggregate_data(self):
        with TemporaryDirectory() as directory:
            output_path = Path(directory) / "robustness.json"
            call_command(
                "run_context_probe_robustness",
                count=12,
                seeds="7,21",
                review_capacities="0,2",
                output=str(output_path),
                stdout=StringIO(),
            )

            payload = json.loads(
                output_path.read_text(encoding="utf-8")
            )

        self.assertEqual(
            payload["experiment"]["controlled_comparisons"],
            4,
        )
        self.assertEqual(len(payload["runs"]), 8)
        self.assertEqual(
            len(payload["capacity_aggregates"]),
            4,
        )
        self.assertIn(
            "robustness_summary",
            payload,
        )

    def test_empty_and_malformed_lists_are_rejected(self):
        for option, value in (
            ("seeds", ""),
            ("seeds", "7,"),
            ("seeds", "seven"),
            ("review_capacities", ""),
            ("review_capacities", "0,"),
            ("review_capacities", "none"),
        ):
            with self.subTest(option=option, value=value):
                with self.assertRaises(CommandError):
                    call_command(
                        "run_context_probe_robustness",
                        count=4,
                        **{option: value},
                        stdout=StringIO(),
                    )

    def test_negative_capacity_and_zero_count_are_rejected(self):
        with self.assertRaises(CommandError):
            call_command(
                "run_context_probe_robustness",
                count=4,
                review_capacities="-1",
                stdout=StringIO(),
            )

        with self.assertRaises(CommandError):
            call_command(
                "run_context_probe_robustness",
                count=0,
                stdout=StringIO(),
            )
