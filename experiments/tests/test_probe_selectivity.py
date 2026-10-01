from datetime import UTC, datetime

from django.test import SimpleTestCase

from experiments.services.probe_selectivity import (
    ProbeSelectivityComparisonService,
)
from experiments.services.scenario_generator import (
    SyntheticScenarioGenerator,
)


class ProbeSelectivityComparisonTests(
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

        self.service = (
            ProbeSelectivityComparisonService()
        )

    def compare(self):
        return self.service.compare(
            self.scenarios,
            review_capacity=5,
        )

    def test_two_probe_policies_are_compared(
        self,
    ):
        result = self.compare()

        strategies = {
            item.strategy
            for item in result.strategies
        }

        self.assertEqual(
            strategies,
            {
                "LEGACY_CONTEXT_PROBE",
                "DECISION_RELEVANT_CONTEXT_PROBE",
            },
        )

    def test_both_use_same_scenario_population(
        self,
    ):
        result = self.compare()

        self.assertEqual(
            len(result.strategies),
            2,
        )

        self.assertTrue(
            all(
                0.0
                <= item.prevention_rate
                <= 1.0
                for item
                in result.strategies
            )
        )

    def test_candidate_does_not_probe_more_than_legacy(
        self,
    ):
        result = self.compare()

        metrics = {
            item.strategy: item
            for item
            in result.strategies
        }

        self.assertLessEqual(
            metrics[
                "DECISION_RELEVANT_CONTEXT_PROBE"
            ].context_probes,
            metrics[
                "LEGACY_CONTEXT_PROBE"
            ].context_probes,
        )

    def test_probe_rates_are_bounded(
        self,
    ):
        result = self.compare()

        for item in result.strategies:
            self.assertGreaterEqual(
                item.probe_rate,
                0.0,
            )

            self.assertLessEqual(
                item.probe_rate,
                1.0,
            )

    def test_negative_capacity_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            self.service.compare(
                self.scenarios,
                review_capacity=-1,
            )