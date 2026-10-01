import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class RunContextProbeMixtureSensitivityCommandTests(
    SimpleTestCase
):
    def test_json_contains_profiles_and_family_counts(self):
        with TemporaryDirectory() as directory:
            output_path = Path(directory) / "mixture.json"
            call_command(
                "run_context_probe_mixture_sensitivity",
                count=24,
                seeds="7,21",
                review_capacities="5,20",
                profiles="EQUAL_FAMILY,NETWORK_ABUSE_HEAVY",
                output=str(output_path),
                stdout=StringIO(),
            )
            payload = json.loads(
                output_path.read_text(encoding="utf-8")
            )

        self.assertEqual(
            payload["experiment"]["profiles"],
            ["EQUAL_FAMILY", "NETWORK_ABUSE_HEAVY"],
        )
        self.assertEqual(len(payload["runs"]), 16)
        self.assertEqual(
            sum(
                payload["cells"][0]["family_counts"].values()
            ),
            24,
        )
        self.assertIn(
            "EQUAL_FAMILY",
            payload["experiment"]["profile_definitions"],
        )

    def test_invalid_lists_profiles_and_capacity_are_rejected(self):
        invalid_options = (
            {"seeds": ""},
            {"review_capacities": "-1"},
            {"profiles": ""},
            {"profiles": "UNKNOWN"},
        )
        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(CommandError):
                    call_command(
                        "run_context_probe_mixture_sensitivity",
                        count=6,
                        **options,
                        stdout=StringIO(),
                    )
