from datetime import UTC, datetime

from django.test import SimpleTestCase

from experiments.services.probe_robustness import (
    ProbeRobustnessService,
)


class ProbeRobustnessServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = ProbeRobustnessService()

    def run_experiment(self):
        return self.service.run(
            count=24,
            seeds=(7, 21),
            review_capacities=(0, 3),
        )

    def test_seed_capacity_cross_product_and_strategies(self):
        result = self.run_experiment()

        self.assertEqual(len(result.cells), 4)
        self.assertEqual(len(result.runs), 8)
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

    def test_same_population_fingerprint_per_controlled_pair(self):
        result = self.run_experiment()

        for seed in result.seeds:
            fingerprints = {
                cell.scenario_fingerprint
                for cell in result.cells
                if cell.seed == seed
            }
            self.assertEqual(len(fingerprints), 1)

    def test_review_allocation_never_exceeds_capacity(self):
        result = self.run_experiment()

        for run in result.runs:
            self.assertLessEqual(
                run.allocated_reviews,
                run.review_capacity,
            )

    def test_zero_capacity_is_supported(self):
        result = self.service.run(
            count=24,
            seeds=(42,),
            review_capacities=(0,),
        )

        self.assertEqual(
            result.runs[0].review_capacity,
            0,
        )
        self.assertTrue(
            all(
                run.allocated_reviews == 0
                for run in result.runs
            )
        )

    def test_aggregate_seed_count_and_bounded_rates(self):
        result = self.run_experiment()

        self.assertTrue(
            all(
                aggregate.seed_count == 2
                for aggregate in result.aggregates
            )
        )
        self.assertTrue(
            all(
                0.0 <= run.probe_rate <= 1.0
                and 0.0 <= run.prevention_rate <= 1.0
                for run in result.runs
            )
        )

    def test_repeated_execution_is_deterministic(self):
        first = self.run_experiment()
        second = self.run_experiment()

        self.assertEqual(first, second)

    def test_negative_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.run(
                count=24,
                seeds=(42,),
                review_capacities=(-1,),
            )
