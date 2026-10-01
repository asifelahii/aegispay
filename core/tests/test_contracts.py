from datetime import UTC, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from core.contracts import (
    InterventionAction,
    InterventionDecision,
    NormalizedTransaction,
    RiskAssessment,
    RiskBand,
    TransactionGroundTruth,
    TransactionType,
)


class NormalizedTransactionTests(SimpleTestCase):
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

    def test_valid_transaction_can_be_created(self):
        transaction = self.make_transaction()

        self.assertEqual(transaction.transaction_id, "TX-000001")
        self.assertEqual(transaction.amount, Decimal("1500.00"))
        self.assertEqual(transaction.transaction_type, TransactionType.P2P)

    def test_missing_sender_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_transaction(sender_id="")

    def test_non_positive_amount_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_transaction(amount=Decimal("0.00"))

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_transaction(
                occurred_at=datetime(2026, 10, 1, 10, 0, 0)
            )

    def test_invalid_pass_through_ratio_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_transaction(
                recipient_pass_through_ratio=1.5
            )

    def test_ground_truth_is_not_part_of_transaction_contract(self):
        transaction = self.make_transaction()

        ground_truth = TransactionGroundTruth(
            is_scam=True,
            scam_type="IMPERSONATION",
        )

        self.assertFalse(hasattr(transaction, "is_scam"))
        self.assertTrue(ground_truth.is_scam)


class RiskContractTests(SimpleTestCase):
    def test_valid_risk_assessment(self):
        assessment = RiskAssessment(
            score=0.82,
            band=RiskBand.HIGH,
        )

        self.assertEqual(assessment.score, 0.82)
        self.assertEqual(assessment.band, RiskBand.HIGH)

    def test_invalid_risk_score_is_rejected(self):
        with self.assertRaises(ValueError):
            RiskAssessment(
                score=1.2,
                band=RiskBand.CRITICAL,
            )

    def test_intervention_decision_can_wrap_risk_assessment(self):
        assessment = RiskAssessment(
            score=0.91,
            band=RiskBand.CRITICAL,
        )

        decision = InterventionDecision(
            action=InterventionAction.HUMAN_REVIEW,
            risk=assessment,
        )

        self.assertEqual(
            decision.action,
            InterventionAction.HUMAN_REVIEW,
        )