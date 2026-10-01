from datetime import UTC, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from core.contracts import (
    DecisionReason,
    InterventionAction,
    NormalizedTransaction,
    RiskAssessment,
    RiskBand,
    ScamContext,
    TransactionType,
)
from interventions.services.decision import (
    AegisPayDecisionService,
    DecisionStatus,
)


class AegisPayDecisionServiceTests(
    SimpleTestCase
):
    def setUp(self):
        self.service = AegisPayDecisionService()

    def make_transaction(
        self,
        *,
        amount="5000.00",
        **overrides,
    ):
        data = {
            "transaction_id": "TX-001",
            "sender_id": "CUS-001",
            "recipient_id": "CUS-002",
            "amount": Decimal(amount),
            "transaction_type": TransactionType.P2P,
            "occurred_at": datetime.now(UTC),
        }

        data.update(overrides)

        return NormalizedTransaction(**data)

    def make_risk(
        self,
        *,
        score,
        band,
        reasons=(),
    ):
        return RiskAssessment(
            score=score,
            band=band,
            reasons=reasons,
        )

    def test_low_risk_can_be_decided_without_context(self):
        decision = self.service.decide(
            transaction=self.make_transaction(),
            base_risk=self.make_risk(
                score=0.10,
                band=RiskBand.LOW,
            ),
        )

        self.assertEqual(
            decision.status,
            DecisionStatus.DECIDED,
        )

        self.assertIsNone(
            decision.context_question
        )

        self.assertIsNotNone(
            decision.policy
        )

        self.assertEqual(
            decision.policy.action,
            InterventionAction.ALLOW,
        )

    def test_medium_risk_can_pause_for_context(self):
        risk = self.make_risk(
            score=0.35,
            band=RiskBand.MEDIUM,
            reasons=(
                DecisionReason(
                    code="NEW_RECIPIENT",
                    message="New recipient.",
                    contribution=0.15,
                ),
                DecisionReason(
                    code="HIGH_AMOUNT_DEVIATION",
                    message="High amount.",
                    contribution=0.20,
                ),
            ),
        )

        decision = self.service.decide(
            transaction=self.make_transaction(
                is_new_recipient=True,
            ),
            base_risk=risk,
        )

        self.assertEqual(
            decision.status,
            DecisionStatus.NEEDS_CONTEXT,
        )

        self.assertIsNotNone(
            decision.context_question
        )

        self.assertIsNone(
            decision.policy
        )

    def test_context_answer_completes_decision(self):
        risk = self.make_risk(
            score=0.30,
            band=RiskBand.MEDIUM,
            reasons=(
                DecisionReason(
                    code="NEW_RECIPIENT",
                    message="New recipient.",
                    contribution=0.15,
                ),
                DecisionReason(
                    code="HIGH_AMOUNT_DEVIATION",
                    message="High amount.",
                    contribution=0.15,
                ),
            ),
        )

        decision = self.service.decide(
            transaction=self.make_transaction(),
            base_risk=risk,
            context=ScamContext(
                phone_call=True,
            ),
        )

        self.assertEqual(
            decision.status,
            DecisionStatus.DECIDED,
        )

        self.assertEqual(
            decision.base_risk.score,
            0.30,
        )

        self.assertEqual(
            decision.final_risk.score,
            0.50,
        )

        self.assertEqual(
            decision.final_risk.band,
            RiskBand.HIGH,
        )

        self.assertIsNotNone(
            decision.policy
        )

    def test_negative_context_preserves_base_risk(self):
        risk = self.make_risk(
            score=0.30,
            band=RiskBand.MEDIUM,
            reasons=(
                DecisionReason(
                    code="BASE_RISK",
                    message="Base evidence.",
                    contribution=0.30,
                ),
            ),
        )

        decision = self.service.decide(
            transaction=self.make_transaction(),
            base_risk=risk,
            context=ScamContext(
                phone_call=False,
                urgency=False,
            ),
        )

        self.assertEqual(
            decision.status,
            DecisionStatus.DECIDED,
        )

        self.assertEqual(
            decision.final_risk.score,
            0.30,
        )

    def test_critical_risk_skips_context_probe(self):
        risk = self.make_risk(
            score=0.80,
            band=RiskBand.CRITICAL,
            reasons=(
                DecisionReason(
                    code="STRONG_BASE_EVIDENCE",
                    message="Strong evidence.",
                    contribution=0.80,
                ),
            ),
        )

        decision = self.service.decide(
            transaction=self.make_transaction(
                amount="1000.00",
            ),
            base_risk=risk,
        )

        self.assertEqual(
            decision.status,
            DecisionStatus.DECIDED,
        )

        self.assertIsNone(
            decision.context_question
        )

        self.assertEqual(
            decision.policy.action,
            InterventionAction.VERIFY,
        )