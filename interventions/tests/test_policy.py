from datetime import UTC, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from core.contracts import (
    InterventionAction,
    NormalizedTransaction,
    RiskAssessment,
    RiskBand,
    TransactionType,
)
from interventions.services.policy import (
    MinimumEffectiveInterventionPolicy,
)


class MinimumEffectiveInterventionPolicyTests(
    SimpleTestCase
):
    def setUp(self):
        self.policy = (
            MinimumEffectiveInterventionPolicy()
        )

    def make_transaction(
        self,
        *,
        amount="5000.00",
    ):
        return NormalizedTransaction(
            transaction_id="TX-001",
            sender_id="CUS-001",
            recipient_id="CUS-002",
            amount=Decimal(amount),
            transaction_type=TransactionType.P2P,
            occurred_at=datetime.now(UTC),
        )

    def make_risk(
        self,
        *,
        score,
        band,
    ):
        return RiskAssessment(
            score=score,
            band=band,
        )

    def test_low_risk_transaction_can_be_allowed(self):
        decision = self.policy.select(
            transaction=self.make_transaction(),
            risk=self.make_risk(
                score=0.10,
                band=RiskBand.LOW,
            ),
        )

        self.assertEqual(
            decision.action,
            InterventionAction.ALLOW,
        )

    def test_medium_risk_can_receive_scam_warning(self):
        decision = self.policy.select(
            transaction=self.make_transaction(),
            risk=self.make_risk(
                score=0.30,
                band=RiskBand.MEDIUM,
            ),
        )

        self.assertEqual(
            decision.action,
            InterventionAction.SCAM_WARNING,
        )

    def test_high_risk_can_require_verification(self):
        decision = self.policy.select(
            transaction=self.make_transaction(),
            risk=self.make_risk(
                score=0.55,
                band=RiskBand.HIGH,
            ),
        )

        self.assertEqual(
            decision.action,
            InterventionAction.VERIFY,
        )

    def test_critical_high_exposure_can_require_review(self):
        decision = self.policy.select(
            transaction=self.make_transaction(),
            risk=self.make_risk(
                score=0.80,
                band=RiskBand.CRITICAL,
            ),
        )

        self.assertEqual(
            decision.action,
            InterventionAction.HUMAN_REVIEW,
        )

    def test_critical_low_value_transaction_uses_minimum_effective_action(
        self,
    ):
        decision = self.policy.select(
            transaction=self.make_transaction(
                amount="1000.00",
            ),
            risk=self.make_risk(
                score=0.80,
                band=RiskBand.CRITICAL,
            ),
        )

        self.assertEqual(
            decision.action,
            InterventionAction.VERIFY,
        )

    def test_transaction_value_can_change_selected_action(self):
        risk = self.make_risk(
            score=0.30,
            band=RiskBand.MEDIUM,
        )

        normal_value = self.policy.select(
            transaction=self.make_transaction(
                amount="5000.00",
            ),
            risk=risk,
        )

        high_value = self.policy.select(
            transaction=self.make_transaction(
                amount="20000.00",
            ),
            risk=risk,
        )

        self.assertNotEqual(
            normal_value.action,
            high_value.action,
        )

        self.assertEqual(
            normal_value.action,
            InterventionAction.SCAM_WARNING,
        )

        self.assertEqual(
            high_value.action,
            InterventionAction.HUMAN_REVIEW,
        )

    def test_expected_exposure_is_calculated(self):
        decision = self.policy.select(
            transaction=self.make_transaction(
                amount="5000.00",
            ),
            risk=self.make_risk(
                score=0.40,
                band=RiskBand.MEDIUM,
            ),
        )

        self.assertEqual(
            decision.expected_fraud_exposure,
            2000.00,
        )

    def test_policy_returns_action_comparisons(self):
        decision = self.policy.select(
            transaction=self.make_transaction(),
            risk=self.make_risk(
                score=0.55,
                band=RiskBand.HIGH,
            ),
        )

        self.assertGreater(
            len(decision.evaluations),
            1,
        )

        selected_evaluation = next(
            evaluation
            for evaluation in decision.evaluations
            if evaluation.action
            == decision.action
        )

        self.assertEqual(
            decision.selected_cost,
            selected_evaluation.total_expected_cost,
        )