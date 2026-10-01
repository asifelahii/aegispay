from datetime import UTC, datetime

from django.test import SimpleTestCase

from experiments.services.baselines import (
    BaselineExperimentRunner,
    BaselineStrategy,
)
from experiments.services.friction import (
    CustomerFrictionAccounting,
    FrictionAssumptions,
)
from experiments.services.runner import (
    AegisPayExperimentRunner,
)
from experiments.services.scenario_generator import (
    SyntheticScenarioGenerator,
)


class CustomerFrictionAccountingTests(
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

    def test_aegispay_accounts_for_legitimate_context_probes(
        self,
    ):
        result = (
            AegisPayExperimentRunner().run(
                self.scenarios,
                review_capacity=5,
            )
        )

        friction = (
            CustomerFrictionAccounting().calculate(
                result
            )
        )

        self.assertGreater(
            friction.legitimate_context_probes,
            0,
        )

        self.assertGreater(
            friction.legitimate_context_probe_friction_cost,
            0,
        )

    def test_static_tier_has_no_context_probe_friction(
        self,
    ):
        result = (
            BaselineExperimentRunner().run(
                self.scenarios,
                strategy=(
                    BaselineStrategy.STATIC_TIER
                ),
                review_capacity=5,
            )
        )

        friction = (
            CustomerFrictionAccounting().calculate(
                result
            )
        )

        self.assertEqual(
            friction.legitimate_context_probes,
            0,
        )

        self.assertEqual(
            friction.legitimate_context_probe_friction_cost,
            0.0,
        )

    def test_total_customer_friction_is_decomposed(
        self,
    ):
        result = (
            AegisPayExperimentRunner().run(
                self.scenarios,
                review_capacity=5,
            )
        )

        friction = (
            CustomerFrictionAccounting().calculate(
                result
            )
        )

        self.assertEqual(
            friction.legitimate_total_customer_friction_cost,
            round(
                (
                    friction.legitimate_intervention_friction_cost
                    + friction.legitimate_context_probe_friction_cost
                ),
                2,
            ),
        )

    def test_custom_probe_cost_is_supported(
        self,
    ):
        result = (
            AegisPayExperimentRunner().run(
                self.scenarios,
                review_capacity=5,
            )
        )

        friction = CustomerFrictionAccounting(
            assumptions=FrictionAssumptions(
                context_probe_cost=10.0,
            )
        ).calculate(
            result
        )

        self.assertEqual(
            friction.legitimate_context_probe_friction_cost,
            (
                friction.legitimate_context_probes
                * 10.0
            ),
        )

    def test_negative_probe_cost_is_rejected(
        self,
    ):
        with self.assertRaises(ValueError):
            FrictionAssumptions(
                context_probe_cost=-1.0
            )