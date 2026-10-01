import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class RunContextProbeFrictionSensitivityCommandTests(
    SimpleTestCase
):
    def test_json_contains_assumptions_and_summaries(self):
        with TemporaryDirectory() as directory:
            output_path = Path(directory) / "friction.json"
            call_command(
                "run_context_probe_friction_sensitivity",
                count=24,
                seeds="7,21",
                review_capacities="5,20",
                profiles="EQUAL_FAMILY,NETWORK_ABUSE_HEAVY",
                probe_costs="0,25,200",
                output=str(output_path),
                stdout=StringIO(),
            )
            payload = json.loads(
                output_path.read_text(encoding="utf-8")
            )

        experiment = payload["experiment"]
        self.assertEqual(
            experiment["probe_costs"],
            [0.0, 25.0, 200.0],
        )
        self.assertEqual(experiment["runtime_executions"], 16)
        self.assertEqual(experiment["evaluation_rows"], 48)
        self.assertIn("cost_summaries", payload)
        self.assertIn("profile_summaries", payload)
        self.assertIn("family_counts", payload["runs"][0])

    def test_malformed_probe_costs_are_rejected(self):
        for value in ("", "0,", "not-a-number", "-1"):
            with self.subTest(value=value):
                with self.assertRaises(CommandError):
                    call_command(
                        "run_context_probe_friction_sensitivity",
                        count=6,
                        probe_costs=value,
                        stdout=StringIO(),
                    )
