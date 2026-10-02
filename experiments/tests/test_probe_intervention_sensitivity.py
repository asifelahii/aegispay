from django.test import SimpleTestCase

from experiments.services.probe_intervention_sensitivity import (
    ProbeInterventionSensitivityService,
)


class ProbeInterventionSensitivityTests(SimpleTestCase):
    def run_experiment(self):
        return ProbeInterventionSensitivityService().run(
            count=24,
            profiles=("EQUAL_FAMILY",),
            seeds=(7, 21),
            review_capacities=(5, 20),
            assumptions=("BASELINE", "HIGH_REVIEW_COST"),
        )

    def test_cross_product_and_shared_populations(self):
        result = self.run_experiment()
        self.assertEqual(len(result.cells), 8)
        self.assertEqual(len(result.runs), 16)
        for cell in result.cells:
            self.assertEqual(
                {run.scenario_fingerprint for run in cell.strategies},
                {cell.scenario_fingerprint},
            )

    def test_capacity_rates_and_distributions(self):
        result = self.run_experiment()
        for run in result.runs:
            self.assertLessEqual(
                run.metrics["allocated_reviews"],
                run.review_capacity,
            )
            self.assertEqual(
                sum(run.requested_action_counts.values()),
                24,
            )
            self.assertEqual(
                sum(run.effective_action_counts.values()),
                24,
            )
            self.assertGreaterEqual(run.metrics["probe_rate"], 0.0)
            self.assertLessEqual(run.metrics["probe_rate"], 1.0)

    def test_repeated_execution_is_deterministic(self):
        self.assertEqual(self.run_experiment(), self.run_experiment())

    def test_per_assumption_and_global_summary_scopes(self):
        result = self.run_experiment()
        self.assertEqual(
            [summary["total_cells"] for summary in result.candidate_summaries],
            [4, 4],
        )
        self.assertEqual(
            result.global_candidate_summary["total_cells"],
            8,
        )
