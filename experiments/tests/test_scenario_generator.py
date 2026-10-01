from datetime import UTC, datetime

from django.test import SimpleTestCase

from experiments.services.scenario_generator import (
    ScenarioType,
    SyntheticScenarioGenerator,
)
from core.contracts import (
    RiskBand,
    TransactionGroundTruth,
)
from risk.services.rules import (
    RulesRiskEngine,
)


class SyntheticScenarioGeneratorTests(
    SimpleTestCase
):
    def test_requested_number_of_scenarios_is_generated(
        self,
    ):
        generator = SyntheticScenarioGenerator(
            seed=42
        )

        scenarios = generator.generate(
            count=12,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        self.assertEqual(
            len(scenarios),
            12,
        )

    def test_generation_is_reproducible_with_same_seed(
        self,
    ):
        first = SyntheticScenarioGenerator(
            seed=123
        ).generate(
            count=6,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        second = SyntheticScenarioGenerator(
            seed=123
        ).generate(
            count=6,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        self.assertEqual(
            first,
            second,
        )

    def test_ground_truth_is_separate_from_transaction(
        self,
    ):
        scenario = SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=2,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )[1]

        self.assertIsInstance(
            scenario.ground_truth,
            TransactionGroundTruth,
        )

        self.assertFalse(
            hasattr(
                scenario.transaction,
                "is_scam",
            )
        )

    def test_legitimate_scenario_is_not_labeled_scam(
        self,
    ):
        scenario = SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=1,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )[0]

        self.assertEqual(
            scenario.scenario_type,
            ScenarioType.LEGITIMATE,
        )

        self.assertFalse(
            scenario.ground_truth.is_scam,
        )

        self.assertIsNone(
            scenario.ground_truth.scam_type,
        )

    def test_account_takeover_has_behavioral_signals(
        self,
    ):
        scenarios = SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=2,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        scenario = scenarios[1]

        self.assertEqual(
            scenario.scenario_type,
            ScenarioType.ACCOUNT_TAKEOVER,
        )

        self.assertTrue(
            scenario.transaction.device_changed_recently
        )

        self.assertGreaterEqual(
            scenario.transaction.sender_tx_count_10m,
            5,
        )

        self.assertTrue(
            scenario.ground_truth.is_scam,
        )

    def test_impersonation_contains_context_signals(
        self,
    ):
        scenarios = SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=3,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        scenario = scenarios[2]

        self.assertEqual(
            scenario.scenario_type,
            ScenarioType.IMPERSONATION,
        )

        self.assertTrue(
            scenario.context.phone_call
        )

        self.assertTrue(
            scenario.context.support_impersonation
        )

    def test_mule_scenario_contains_network_signals(
        self,
    ):
        scenarios = SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=5,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        scenario = scenarios[4]

        self.assertEqual(
            scenario.scenario_type,
            ScenarioType.MULE_RECIPIENT,
        )

        self.assertGreaterEqual(
            scenario.transaction.recipient_unique_senders_24h,
            10,
        )

        self.assertGreaterEqual(
            scenario.transaction.recipient_pass_through_ratio,
            0.80,
        )

    def test_negative_count_is_rejected(self):
        generator = SyntheticScenarioGenerator()

        with self.assertRaises(ValueError):
            generator.generate(
                count=-1
            )

    def test_unusual_legitimate_scenario_is_not_scam(
        self,
    ):
        scenarios = SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=7,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        scenario = scenarios[6]

        self.assertEqual(
            scenario.scenario_type,
            ScenarioType.LEGITIMATE_UNUSUAL,
        )

        self.assertFalse(
            scenario.ground_truth.is_scam,
        )

        self.assertTrue(
            scenario.transaction.is_new_recipient
        )

        self.assertGreater(
            scenario.transaction.amount_vs_sender_mean,
            2.0,
        )
    

    def test_legitimate_network_hub_is_not_scam(
        self,
    ):
        scenarios = SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=8,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        scenario = scenarios[7]

        self.assertEqual(
            scenario.scenario_type,
            ScenarioType.LEGITIMATE_NETWORK_HUB,
        )

        self.assertFalse(
            scenario.ground_truth.is_scam,
        )

        self.assertGreaterEqual(
            scenario.transaction.recipient_unique_senders_24h,
            10,
        )

    def test_hard_negative_legitimate_scenarios_can_look_risky(
        self,
    ):
        scenarios = SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=8,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        engine = RulesRiskEngine()

        unusual = engine.assess(
            scenarios[6].transaction
        )

        network_hub = engine.assess(
            scenarios[7].transaction
        )

        self.assertGreaterEqual(
            unusual.score,
            0.25,
        )

        self.assertGreaterEqual(
            network_hub.score,
            0.25,
        )

        self.assertNotEqual(
            unusual.band,
            RiskBand.LOW,
        )

        self.assertNotEqual(
            network_hub.band,
            RiskBand.LOW,
        )

    def test_first_eight_scenarios_include_three_legitimate_families(
        self,
    ):
        scenarios = SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=8,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        legitimate_types = {
            scenario.scenario_type
            for scenario in scenarios
            if not scenario.ground_truth.is_scam
        }

        self.assertEqual(
            legitimate_types,
            {
                ScenarioType.LEGITIMATE,
                ScenarioType.LEGITIMATE_UNUSUAL,
                ScenarioType.LEGITIMATE_NETWORK_HUB,
            },
        )


    def test_all_declared_scam_types_are_labeled_scam(
        self,
    ):
        scenarios = SyntheticScenarioGenerator(
            seed=42
        ).generate(
            count=8,
            start_time=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
        )

        for scenario in scenarios:
            expected = (
                scenario.scenario_type
                in SyntheticScenarioGenerator.SCAM_TYPES
            )

            self.assertEqual(
                scenario.ground_truth.is_scam,
                expected,
            )