from django.test import SimpleTestCase

from experiments.services.probe_friction_sensitivity import (
    ProbeFrictionSensitivityService,
)


class ProbeFrictionSensitivityServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = ProbeFrictionSensitivityService()

    def run_experiment(self):
        return self.service.run(
            count=48,
            profiles=(
                "EQUAL_FAMILY",
                "HARD_NEGATIVE_DOMINANT",
            ),
            seeds=(7, 21),
            review_capacities=(5, 20),
            probe_costs=(0.0, 25.0, 200.0),
        )

    def test_base_cross_product_and_all_assumptions(self):
        result = self.run_experiment()

        self.assertEqual(result.base_runtime_cells, 8)
        self.assertEqual(result.runtime_executions, 16)
        self.assertEqual(result.evaluation_cells, 24)
        self.assertEqual(result.evaluation_rows, 48)
        self.assertEqual(
            {
                run.strategy
                for run in result.runs
            },
            {
                "LEGACY_CONTEXT_PROBE",
                "DECISION_RELEVANT_CONTEXT_PROBE",
            },
        )

    def test_probe_cost_preserves_runtime_outcomes(self):
        result = self.run_experiment()
        self.assertTrue(result.invariant)
        self.assertEqual(result.invariant_violations, ())

        grouped = {}
        for run in result.runs:
            key = (
                run.profile,
                run.seed,
                run.review_capacity,
                run.strategy,
            )
            grouped.setdefault(key, []).append(run)

        fields = (
            "context_probes",
            "probe_rate",
            "prevention_rate",
            "prevented_scam_value",
            "residual_scam_loss",
            "requested_reviews",
            "allocated_reviews",
            "operations_cost",
            "legitimate_intervention_friction",
        )
        for runs in grouped.values():
            for field in fields:
                self.assertEqual(
                    len({getattr(run, field) for run in runs}),
                    1,
                )

    def test_probe_friction_changes_with_cost_and_zero_is_supported(self):
        result = self.run_experiment()
        for key in (
            ("EQUAL_FAMILY", 7, 5, "LEGACY_CONTEXT_PROBE"),
            (
                "EQUAL_FAMILY",
                7,
                5,
                "DECISION_RELEVANT_CONTEXT_PROBE",
            ),
        ):
            runs = [
                run
                for run in result.runs
                if (
                    run.profile,
                    run.seed,
                    run.review_capacity,
                    run.strategy,
                ) == key
            ]
            self.assertEqual(
                runs[0].legitimate_probe_friction,
                0.0,
            )
            self.assertLess(
                runs[0].legitimate_probe_friction,
                runs[-1].legitimate_probe_friction,
            )

    def test_rates_are_bounded_and_execution_is_deterministic(self):
        first = self.run_experiment()
        second = self.run_experiment()

        self.assertEqual(first, second)
        self.assertTrue(
            all(
                0.0 <= run.probe_rate <= 1.0
                and 0.0 <= run.prevention_rate <= 1.0
                for run in first.runs
            )
        )

    def test_negative_probe_cost_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.run(
                count=12,
                profiles=("EQUAL_FAMILY",),
                seeds=(42,),
                review_capacities=(5,),
                probe_costs=(-1.0,),
            )
