from datetime import UTC, datetime

from django.test import SimpleTestCase

from core.contracts import InterventionAction
from experiments.services.baselines import (
    BaselineExperimentRunner,
    BaselineStrategy,
)
from experiments.services.scenario_generator import (
    SyntheticScenarioGenerator,
)


class BaselineExperimentRunnerTests(
    SimpleTestCase
):
    def setUp(self):
        self.runner = (
            BaselineExperimentRunner()
        )

        self.scenarios = (
            SyntheticScenarioGenerator(
                seed=42
            ).generate(
                count=12,
                start_time=datetime(
                    2026,
                    10,
                    1,
                    tzinfo=UTC,
                ),
            )
        )

    def test_no_intervention_allows_everything(self):
        result = self.runner.run(
            self.scenarios,
            strategy=(
                BaselineStrategy.NO_INTERVENTION
            ),
            review_capacity=2,
        )

        self.assertTrue(
            all(
                outcome.effective_action
                == InterventionAction.ALLOW
                for outcome in result.outcomes
            )
        )

        self.assertEqual(
            result.summary.prevented_scam_value,
            0.0,
        )

        self.assertEqual(
            result.summary.requested_reviews,
            0,
        )

    def test_no_baseline_uses_context_probe(self):
        for strategy in (
            BaselineStrategy.NO_INTERVENTION,
            BaselineStrategy.HARD_THRESHOLD,
            BaselineStrategy.STATIC_TIER,
        ):
            result = self.runner.run(
                self.scenarios,
                strategy=strategy,
                review_capacity=2,
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

    def test_hard_threshold_requests_review_for_high_scores(
        self,
    ):
        result = self.runner.run(
            self.scenarios,
            strategy=(
                BaselineStrategy.HARD_THRESHOLD
            ),
            review_capacity=10,
        )

        review_outcomes = [
            outcome
            for outcome in result.outcomes
            if outcome.review_requested
        ]

        self.assertGreater(
            len(review_outcomes),
            0,
        )

        self.assertTrue(
            all(
                outcome.base_risk_score
                >= 0.50
                for outcome
                in review_outcomes
            )
        )

    def test_hard_threshold_respects_review_capacity(
        self,
    ):
        result = self.runner.run(
            self.scenarios,
            strategy=(
                BaselineStrategy.HARD_THRESHOLD
            ),
            review_capacity=1,
        )

        self.assertLessEqual(
            result.summary.allocated_reviews,
            1,
        )

        allocated = sum(
            1
            for outcome in result.outcomes
            if outcome.review_allocated
        )

        self.assertEqual(
            allocated,
            result.summary.allocated_reviews,
        )

    def test_static_tier_maps_medium_to_contextual_warning(
        self,
    ):
        result = self.runner.run(
            self.scenarios,
            strategy=(
                BaselineStrategy.STATIC_TIER
            ),
            review_capacity=2,
        )

        medium_outcomes = [
            outcome
            for outcome in result.outcomes
            if (
                0.25
                <= outcome.base_risk_score
                < 0.50
            )
        ]

        self.assertGreater(
            len(medium_outcomes),
            0,
        )

        self.assertTrue(
            all(
                outcome.requested_action
                == InterventionAction.CONTEXTUAL_WARNING
                for outcome
                in medium_outcomes
            )
        )

    def test_scam_value_is_conserved(self):
        result = self.runner.run(
            self.scenarios,
            strategy=(
                BaselineStrategy.STATIC_TIER
            ),
            review_capacity=2,
        )

        self.assertAlmostEqual(
            result.summary.total_scam_value,
            (
                result.summary.prevented_scam_value
                + result.summary.residual_scam_loss
            ),
            places=2,
        )

    def test_negative_review_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.runner.run(
                self.scenarios,
                strategy=(
                    BaselineStrategy.HARD_THRESHOLD
                ),
                review_capacity=-1,
            )