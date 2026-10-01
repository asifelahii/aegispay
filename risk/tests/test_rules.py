from datetime import UTC, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from core.contracts import (
    NormalizedTransaction,
    RiskBand,
    TransactionType,
)
from risk.services.rules import RulesRiskEngine


class RulesRiskEngineTests(SimpleTestCase):
    def setUp(self):
        self.engine = RulesRiskEngine()

    def make_transaction(self, **overrides):
        data = {
            "transaction_id": "TX-000001",
            "sender_id": "CUS-001",
            "recipient_id": "CUS-002",
            "amount": Decimal("1500.00"),
            "transaction_type": TransactionType.P2P,
            "occurred_at": datetime.now(UTC),
        }

        data.update(overrides)

        return NormalizedTransaction(**data)

    def test_normal_transaction_is_low_risk(self):
        transaction = self.make_transaction()

        assessment = self.engine.assess(transaction)

        self.assertEqual(assessment.score, 0.0)
        self.assertEqual(assessment.band, RiskBand.LOW)
        self.assertEqual(len(assessment.reasons), 0)

    def test_new_recipient_adds_risk(self):
        transaction = self.make_transaction(
            is_new_recipient=True,
        )

        assessment = self.engine.assess(transaction)

        self.assertEqual(assessment.score, 0.15)

        reason_codes = {
            reason.code
            for reason in assessment.reasons
        }

        self.assertIn("NEW_RECIPIENT", reason_codes)

    def test_multiple_signals_accumulate_risk(self):
        transaction = self.make_transaction(
            is_new_recipient=True,
            device_changed_recently=True,
            amount_vs_sender_mean=3.5,
            amount_vs_sender_p95=1.5,
        )

        assessment = self.engine.assess(transaction)

        self.assertEqual(assessment.score, 0.60)
        self.assertEqual(assessment.band, RiskBand.HIGH)

    def test_mule_like_recipient_can_be_critical(self):
        transaction = self.make_transaction(
            is_new_recipient=True,
            amount_vs_sender_mean=3.5,
            amount_vs_sender_p95=1.5,
            recipient_unique_senders_24h=25,
            recipient_fan_in_24h=30,
            recipient_pass_through_ratio=0.90,
            recipient_cashout_velocity_1h=0.85,
        )

        assessment = self.engine.assess(transaction)

        self.assertEqual(assessment.score, 0.85)
        self.assertEqual(
            assessment.band,
            RiskBand.CRITICAL,
        )

        reason_codes = {
            reason.code
            for reason in assessment.reasons
        }

        self.assertIn(
            "HIGH_RECIPIENT_FAN_IN",
            reason_codes,
        )
        self.assertIn(
            "HIGH_PASS_THROUGH",
            reason_codes,
        )
        self.assertIn(
            "RAPID_CASHOUT",
            reason_codes,
        )

    def test_score_is_capped_at_one(self):
        transaction = self.make_transaction(
            is_new_recipient=True,
            device_changed_recently=True,
            amount_vs_sender_mean=4.0,
            amount_vs_sender_p95=2.0,
            sender_tx_count_10m=10,
            recipient_unique_senders_24h=30,
            recipient_fan_in_24h=50,
            recipient_pass_through_ratio=0.95,
            recipient_cashout_velocity_1h=0.95,
        )

        assessment = self.engine.assess(transaction)

        self.assertEqual(assessment.score, 1.0)
        self.assertEqual(
            assessment.band,
            RiskBand.CRITICAL,
        )