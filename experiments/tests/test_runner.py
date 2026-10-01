from dataclasses import replace
from datetime import UTC, datetime

from django.test import SimpleTestCase

from core.contracts import (
    TransactionGroundTruth,
)
from experiments.services.runner import (
    AegisPayExperimentRunner,
)
from experiments.services.scenario_generator import (
    SyntheticScenarioGenerator,
)


class AegisPayExperimentRunnerTests(
    SimpleTestCase
):
    def setUp(self):
        self.start_time = datetime(
            2026,
            10,
            1,
            tzinfo=UTC,
        )

    def make_scenarios(
        self,
        count=6,
    ):
        return SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=count,
            start_time=self.start_time,
        )

    def test_every_scenario_produces_an_outcome(self):
        scenarios = self.make_scenarios(
            count=12
        )

        result = AegisPayExperimentRunner().run(
            scenarios,
            review_capacity=2,
        )

        self.assertEqual(
            len(result.outcomes),
            12,
        )

        self.assertEqual(
            result.summary.total_scenarios,
            12,
        )

    def test_context_probe_is_selective(self):
        scenarios = self.make_scenarios(
            count=6
        )

        result = AegisPayExperimentRunner().run(
            scenarios,
            review_capacity=2,
        )

        self.assertGreater(
            result.summary.context_probes,
            0,
        )

        self.assertLess(
            result.summary.context_probes,
            6,
        )

    def test_review_capacity_is_respected(self):
        scenarios = self.make_scenarios(
            count=18
        )

        result = AegisPayExperimentRunner().run(
            scenarios,
            review_capacity=2,
        )

        self.assertLessEqual(
            result.summary.allocated_reviews,
            2,
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

    def test_scam_value_is_conserved(self):
        scenarios = self.make_scenarios(
            count=12
        )

        result = AegisPayExperimentRunner().run(
            scenarios,
            review_capacity=3,
        )

        self.assertAlmostEqual(
            result.summary.total_scam_value,
            (
                result.summary.prevented_scam_value
                + result.summary.residual_scam_loss
            ),
            places=2,
        )

    def test_ground_truth_does_not_change_runtime_decision(
        self,
    ):
        scenario = self.make_scenarios(
            count=2
        )[1]

        flipped = replace(
            scenario,
            ground_truth=TransactionGroundTruth(
                is_scam=False,
                scam_type=None,
            ),
        )

        runner = AegisPayExperimentRunner()

        original_result = runner.run(
            [scenario],
            review_capacity=1,
        )

        flipped_result = runner.run(
            [flipped],
            review_capacity=1,
        )

        original = (
            original_result.outcomes[0]
        )

        changed = (
            flipped_result.outcomes[0]
        )

        self.assertEqual(
            original.base_risk_score,
            changed.base_risk_score,
        )

        self.assertEqual(
            original.final_risk_score,
            changed.final_risk_score,
        )

        self.assertEqual(
            original.effective_action,
            changed.effective_action,
        )

    def test_same_scenarios_produce_reproducible_results(
        self,
    ):
        scenarios = self.make_scenarios(
            count=12
        )

        first = AegisPayExperimentRunner().run(
            scenarios,
            review_capacity=2,
        )

        second = AegisPayExperimentRunner().run(
            scenarios,
            review_capacity=2,
        )

        self.assertEqual(
            first,
            second,
        )

    def test_duplicate_transaction_ids_are_rejected(
        self,
    ):
        scenario = self.make_scenarios(
            count=1
        )[0]

        with self.assertRaises(ValueError):
            AegisPayExperimentRunner().run(
                [
                    scenario,
                    scenario,
                ],
                review_capacity=1,
            )