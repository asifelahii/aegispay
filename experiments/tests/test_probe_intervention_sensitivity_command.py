import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class ProbeInterventionSensitivityCommandTests(SimpleTestCase):
    def test_json_contains_materialized_assumptions_and_actions(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "sensitivity.json"
            call_command(
                "run_context_probe_intervention_sensitivity",
                count=12,
                seeds="7",
                review_capacities="5",
                profiles="EQUAL_FAMILY",
                assumptions="BASELINE,HIGH_REVIEW_COST",
                output=str(output),
                stdout=StringIO(),
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["experiment"]["controlled_cells"], 2)
        self.assertIn(
            "intervention_profiles",
            payload["experiment"]["assumption_definitions"]["BASELINE"],
        )
        self.assertIn("requested_action_counts", payload["runs"][0])
        self.assertIn("effective_action_counts", payload["runs"][0])

    def test_invalid_inputs_are_rejected(self):
        for options in (
            {"assumptions": "UNKNOWN"},
            {"assumptions": ""},
            {"review_capacities": "-1"},
            {"seeds": "bad"},
        ):
            with self.subTest(options=options):
                with self.assertRaises(CommandError):
                    call_command(
                        "run_context_probe_intervention_sensitivity",
                        count=6,
                        **options,
                        stdout=StringIO(),
                    )
