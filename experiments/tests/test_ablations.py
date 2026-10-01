from datetime import UTC, datetime

from django.test import SimpleTestCase

from experiments.services.ablations import (
    ContextProbeAblationService,
    NoContextProbeExperimentRunner,
)
from experiments.services.scenario_generator import (
    SyntheticScenarioGenerator,
)


class ContextProbeAblationTests(
    SimpleTestCase
):
    def setUp(self):
        self.scenarios = (
            SyntheticScenarioGenerator(
                seed=42
            ).generate(
                count=80,
                start_time=datetime(
                    2026,
                    10,
                    1,
                    tzinfo=UTC,
                ),
            )
        )

    def test_no_probe_runner_never_requests_context(
        self,
    ):
        result = (
            NoContextProbeExperimentRunner().run(
                self.scenarios,
                review_capacity=5,
            )
        )

        self.assertEqual(
            result.summary.context_probes,
            0,
        )

        self.assertTrue(
            all(
                not outcome.context_requested
                for outcome
                in result.outcomes
            )
        )

    def test_no_probe_final_risk_equals_base_risk(
        self,
    ):
        result = (
            NoContextProbeExperimentRunner().run(
                self.scenarios,
                review_capacity=5,
            )
        )

        self.assertTrue(
            all(
                outcome.base_risk_score
                == outcome.final_risk_score
                for outcome
                in result.outcomes
            )
        )

    def test_ablation_compares_two_versions(
        self,
    ):
        result = (
            ContextProbeAblationService().compare(
                self.scenarios,
                review_capacity=5,
            )
        )

        strategies = {
            item.strategy
            for item
            in result.strategies
        }

        self.assertEqual(
            strategies,
            {
                "AEGISPAY_NO_CONTEXT_PROBE",
                "AEGISPAY",
            },
        )

    def test_full_aegispay_uses_context_probe(
        self,
    ):
        result = (
            ContextProbeAblationService().compare(
                self.scenarios,
                review_capacity=5,
            )
        )

        metrics = {
            item.strategy: item
            for item
            in result.strategies
        }

        self.assertGreater(
            metrics[
                "AEGISPAY"
            ].context_probes,
            0,
        )

        self.assertEqual(
            metrics[
                "AEGISPAY_NO_CONTEXT_PROBE"
            ].context_probes,
            0,
        )

    def test_no_probe_has_zero_probe_friction(
        self,
    ):
        result = (
            ContextProbeAblationService().compare(
                self.scenarios,
                review_capacity=5,
            )
        )

        metrics = {
            item.strategy: item
            for item
            in result.strategies
        }

        self.assertEqual(
            metrics[
                "AEGISPAY_NO_CONTEXT_PROBE"
            ].legitimate_probe_friction,
            0.0,
        )

    def test_same_ground_truth_value_is_compared(
        self,
    ):
        no_probe = (
            NoContextProbeExperimentRunner().run(
                self.scenarios,
                review_capacity=5,
            )
        )

        from experiments.services.runner import (
            AegisPayExperimentRunner,
        )

        full = (
            AegisPayExperimentRunner().run(
                self.scenarios,
                review_capacity=5,
            )
        )

        self.assertEqual(
            no_probe.summary.total_scam_value,
            full.summary.total_scam_value,
        )

    def test_review_capacity_is_respected(
        self,
    ):
        result = (
            ContextProbeAblationService().compare(
                self.scenarios,
                review_capacity=2,
            )
        )

        self.assertTrue(
            all(
                item.allocated_reviews <= 2
                for item
                in result.strategies
            )
        )

    def test_negative_capacity_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            ContextProbeAblationService().compare(
                self.scenarios,
                review_capacity=-1,
            )