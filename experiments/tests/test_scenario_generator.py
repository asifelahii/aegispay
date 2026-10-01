from datetime import UTC, datetime

from django.test import SimpleTestCase

from core.contracts import TransactionGroundTruth
from experiments.services.scenario_generator import (
    ScenarioType,
    SyntheticScenarioGenerator,
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