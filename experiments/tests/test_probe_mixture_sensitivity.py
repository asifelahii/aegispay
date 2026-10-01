from django.test import SimpleTestCase

from experiments.services.probe_mixture_sensitivity import (
    ProbeMixtureSensitivityService,
)


class ProbeMixtureSensitivityServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = ProbeMixtureSensitivityService()

    def run_experiment(self):
        return self.service.run(
            count=48,
            profiles=(
                "EQUAL_FAMILY",
                "HARD_NEGATIVE_DOMINANT",
            ),
            seeds=(7, 21),
            review_capacities=(5, 20),
        )

    def test_full_cross_product_and_both_strategies(self):
        result = self.run_experiment()

        self.assertEqual(len(result.cells), 8)
        self.assertEqual(len(result.runs), 16)
        self.assertEqual(
            {
                item.strategy
                for item in result.runs
            },
            {
                "LEGACY_CONTEXT_PROBE",
                "DECISION_RELEVANT_CONTEXT_PROBE",
            },
        )

    def test_same_population_per_controlled_cell(self):
        result = self.run_experiment()

        for cell in result.cells:
            self.assertTrue(
                all(
                    run.scenario_fingerprint
                    == cell.scenario_fingerprint
                    for run in cell.strategies
                )
            )
            self.assertEqual(
                sum(cell.family_counts.values()),
                48,
            )

    def test_capacity_rates_and_aggregate_counts(self):
        result = self.run_experiment()

        self.assertTrue(
            all(
                run.allocated_reviews <= run.review_capacity
                and 0.0 <= run.probe_rate <= 1.0
                and 0.0 <= run.prevention_rate <= 1.0
                for run in result.runs
            )
        )
        self.assertTrue(
            all(
                aggregate.seed_count == 2
                for aggregate in result.aggregates
            )
        )
        self.assertTrue(
            all(
                summary.total_cells == 4
                for summary in result.profile_summaries
            )
        )

    def test_repeated_execution_is_deterministic(self):
        self.assertEqual(
            self.run_experiment(),
            self.run_experiment(),
        )
