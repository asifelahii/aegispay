from datetime import UTC, datetime

from django.test import SimpleTestCase

from experiments.services.baselines import (
    BaselineStrategy,
)
from experiments.services.comparison import (
    PolicyComparisonService,
)
from experiments.services.scenario_generator import (
    SyntheticScenarioGenerator,
)


class PolicyComparisonServiceTests(
    SimpleTestCase
):
    def setUp(self):
        self.service = (
            PolicyComparisonService()
        )

        self.scenarios = (
            SyntheticScenarioGenerator(
                seed=42
            ).generate(
                count=24,
                start_time=datetime(
                    2026,
                    10,
                    1,
                    tzinfo=UTC,
                ),
            )
        )

    def metrics_by_strategy(
        self,
        result,
    ):
        return {
            metrics.strategy: metrics
            for metrics
            in result.strategies
        }

    def test_all_four_strategies_are_compared(self):
        result = self.service.compare(
            self.scenarios,
            review_capacity=3,
        )

        strategies = {
            metrics.strategy
            for metrics
            in result.strategies
        }

        self.assertEqual(
            strategies,
            {
                BaselineStrategy.NO_INTERVENTION.value,
                BaselineStrategy.HARD_THRESHOLD.value,
                BaselineStrategy.STATIC_TIER.value,
                "AEGISPAY",
            },
        )

    def test_all_strategies_use_same_scenario_count(self):
        result = self.service.compare(
            self.scenarios,
            review_capacity=3,
        )

        self.assertTrue(
            all(
                metrics.total_scenarios
                == len(self.scenarios)
                for metrics
                in result.strategies
            )
        )

    def test_no_intervention_has_zero_prevention(self):
        result = self.service.compare(
            self.scenarios,
            review_capacity=3,
        )

        metrics = self.metrics_by_strategy(
            result
        )[
            BaselineStrategy.NO_INTERVENTION.value
        ]

        self.assertEqual(
            metrics.prevented_scam_value,
            0.0,
        )

        self.assertEqual(
            metrics.prevention_rate,
            0.0,
        )

    def test_only_aegispay_uses_context_probe(self):
        result = self.service.compare(
            self.scenarios,
            review_capacity=3,
        )

        metrics = self.metrics_by_strategy(
            result
        )

        self.assertEqual(
            metrics[
                BaselineStrategy.NO_INTERVENTION.value
            ].context_probes,
            0,
        )

        self.assertEqual(
            metrics[
                BaselineStrategy.HARD_THRESHOLD.value
            ].context_probes,
            0,
        )

        self.assertEqual(
            metrics[
                BaselineStrategy.STATIC_TIER.value
            ].context_probes,
            0,
        )

        self.assertGreater(
            metrics[
                "AEGISPAY"
            ].context_probes,
            0,
        )

    def test_review_capacity_is_shared_consistently(
        self,
    ):
        result = self.service.compare(
            self.scenarios,
            review_capacity=2,
        )

        self.assertTrue(
            all(
                metrics.allocated_reviews <= 2
                for metrics
                in result.strategies
            )
        )

    def test_total_modeled_cost_is_calculated(self):
        result = self.service.compare(
            self.scenarios,
            review_capacity=3,
        )

        for metrics in result.strategies:
            expected = round(
                (
                    metrics.residual_scam_loss
                    + metrics.legitimate_total_customer_friction_cost
                    + metrics.operations_cost
                ),
                2,
            )

            self.assertEqual(
                metrics.total_modeled_cost,
                expected,
            )

    def test_baselines_have_zero_context_probe_friction(
        self,
    ):
        result = self.service.compare(
            self.scenarios,
            review_capacity=3,
        )

        metrics = self.metrics_by_strategy(
            result
        )

        for strategy in (
            BaselineStrategy.NO_INTERVENTION.value,
            BaselineStrategy.HARD_THRESHOLD.value,
            BaselineStrategy.STATIC_TIER.value,
        ):
            self.assertEqual(
                metrics[
                    strategy
                ].legitimate_context_probe_friction_cost,
                0.0,
            )

    def test_aegispay_includes_context_probe_friction(
        self,
    ):
        result = self.service.compare(
            self.scenarios,
            review_capacity=3,
        )

        metrics = self.metrics_by_strategy(
            result
        )["AEGISPAY"]

        self.assertGreater(
            metrics.legitimate_context_probe_friction_cost,
            0,
        )

    def test_customer_friction_is_decomposed(
        self,
    ):
        result = self.service.compare(
            self.scenarios,
            review_capacity=3,
        )

        metrics = self.metrics_by_strategy(
            result
        )["AEGISPAY"]

        self.assertEqual(
            metrics.legitimate_total_customer_friction_cost,
            round(
                (
                    metrics.legitimate_friction_cost
                    + metrics.legitimate_context_probe_friction_cost
                ),
                2,
            ),
        )

    def test_prevention_rate_is_bounded(self):
        result = self.service.compare(
            self.scenarios,
            review_capacity=3,
        )

        for metrics in result.strategies:
            self.assertGreaterEqual(
                metrics.prevention_rate,
                0.0,
            )

            self.assertLessEqual(
                metrics.prevention_rate,
                1.0,
            )

    def test_negative_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.compare(
                self.scenarios,
                review_capacity=-1,
            )