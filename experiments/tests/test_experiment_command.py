import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import (
    call_command,
)
from django.core.management.base import (
    CommandError,
)
from django.test import SimpleTestCase


class RunAegisPayExperimentCommandTests(
    SimpleTestCase
):
    def test_command_runs_successfully(self):
        output = StringIO()

        call_command(
            "run_aegispay_experiment",
            count=12,
            seed=42,
            review_capacity=2,
            stdout=output,
        )

        text = output.getvalue()

        self.assertIn(
            "AegisPay Policy Comparison",
            text,
        )

        self.assertIn(
            "NO_INTERVENTION",
            text,
        )

        self.assertIn(
            "HARD_THRESHOLD",
            text,
        )

        self.assertIn(
            "STATIC_TIER",
            text,
        )

        self.assertIn(
            "AEGISPAY",
            text,
        )

    def test_command_can_export_json(self):
        with TemporaryDirectory() as directory:
            output_path = (
                Path(directory)
                / "experiment.json"
            )

            call_command(
                "run_aegispay_experiment",
                count=12,
                seed=42,
                review_capacity=2,
                output=str(
                    output_path
                ),
                stdout=StringIO(),
            )

            self.assertTrue(
                output_path.exists()
            )

            payload = json.loads(
                output_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                payload[
                    "experiment"
                ][
                    "scenario_count"
                ],
                12,
            )

            self.assertEqual(
                payload[
                    "experiment"
                ][
                    "seed"
                ],
                42,
            )

            self.assertEqual(
                len(
                    payload[
                        "strategies"
                    ]
                ),
                4,
            )

    def test_export_contains_all_strategies(self):
        with TemporaryDirectory() as directory:
            output_path = (
                Path(directory)
                / "experiment.json"
            )

            call_command(
                "run_aegispay_experiment",
                count=12,
                seed=42,
                review_capacity=2,
                output=str(
                    output_path
                ),
                stdout=StringIO(),
            )

            payload = json.loads(
                output_path.read_text(
                    encoding="utf-8"
                )
            )

            strategies = {
                item["strategy"]
                for item
                in payload["strategies"]
            }

            self.assertEqual(
                strategies,
                {
                    "NO_INTERVENTION",
                    "HARD_THRESHOLD",
                    "STATIC_TIER",
                    "AEGISPAY",
                },
            )

    def test_export_declares_synthetic_source(self):
        with TemporaryDirectory() as directory:
            output_path = (
                Path(directory)
                / "experiment.json"
            )

            call_command(
                "run_aegispay_experiment",
                count=6,
                output=str(
                    output_path
                ),
                stdout=StringIO(),
            )

            payload = json.loads(
                output_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                payload[
                    "experiment"
                ][
                    "scenario_source"
                ],
                "synthetic_prototype",
            )

            self.assertEqual(
                payload[
                    "experiment"
                ][
                    "ground_truth_usage"
                ],
                "evaluation_only",
            )

    def test_same_seed_produces_same_strategy_results(
        self,
    ):
        first = StringIO()
        second = StringIO()

        call_command(
            "run_aegispay_experiment",
            count=24,
            seed=123,
            review_capacity=3,
            stdout=first,
        )

        call_command(
            "run_aegispay_experiment",
            count=24,
            seed=123,
            review_capacity=3,
            stdout=second,
        )

        self.assertEqual(
            first.getvalue(),
            second.getvalue(),
        )

    def test_zero_count_is_rejected(self):
        with self.assertRaises(
            CommandError
        ):
            call_command(
                "run_aegispay_experiment",
                count=0,
                stdout=StringIO(),
            )

    def test_negative_review_capacity_is_rejected(
        self,
    ):
        with self.assertRaises(
            CommandError
        ):
            call_command(
                "run_aegispay_experiment",
                count=6,
                review_capacity=-1,
                stdout=StringIO(),
            )