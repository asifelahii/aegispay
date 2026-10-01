from datetime import UTC, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from core.contracts import (
    DecisionReason,
    NormalizedTransaction,
    RiskAssessment,
    RiskBand,
    ScamContext,
    TransactionType,
)
from interventions.services.context_probe import (
    ContextProbeService,
)


class ContextProbeServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = ContextProbeService()

    def make_transaction(self, **overrides):
        data = {
            "transaction_id": "TX-001",
            "sender_id": "CUS-001",
            "recipient_id": "CUS-002",
            "amount": Decimal("5000.00"),
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

    def test_low_risk_transaction_is_not_probed(self):
        result = self.service.evaluate(
            transaction=self.make_transaction(),
            risk=self.make_risk(
                score=0.10,
                band=RiskBand.LOW,
            ),
        )

        self.assertFalse(result.should_ask)
        self.assertIsNone(result.question)

    def test_critical_transaction_is_not_probed(self):
        result = self.service.evaluate(
            transaction=self.make_transaction(),
            risk=self.make_risk(
                score=0.90,
                band=RiskBand.CRITICAL,
            ),
        )

        self.assertFalse(result.should_ask)
        self.assertIsNone(result.question)

    def test_medium_risk_can_trigger_one_question(self):
        result = self.service.evaluate(
            transaction=self.make_transaction(
                is_new_recipient=True,
            ),
            risk=self.make_risk(
                score=0.35,
                band=RiskBand.MEDIUM,
                reasons=(
                    DecisionReason(
                        code="NEW_RECIPIENT",
                        message="New recipient.",
                        contribution=0.15,
                    ),
                ),
            ),
        )

        self.assertTrue(result.should_ask)
        self.assertIsNotNone(result.question)

        self.assertEqual(
            result.question.code,
            "ACTIVE_PHONE_OR_CHAT",
        )

    def test_unanswered_question_is_preferred(self):
        context = ScamContext(
            phone_call=False,
        )

        result = self.service.evaluate(
            transaction=self.make_transaction(
                is_new_recipient=True,
            ),
            risk=self.make_risk(
                score=0.40,
                band=RiskBand.MEDIUM,
                reasons=(
                    DecisionReason(
                        code="NEW_RECIPIENT",
                        message="New recipient.",
                        contribution=0.15,
                    ),
                ),
            ),
            context=context,
        )

        self.assertTrue(result.should_ask)

        self.assertNotEqual(
            result.question.answer_key,
            "phone_call",
        )

    def test_amount_anomaly_prioritizes_phone_context(self):
        result = self.service.evaluate(
            transaction=self.make_transaction(
                is_new_recipient=True,
                amount_vs_sender_mean=4.0,
            ),
            risk=self.make_risk(
                score=0.55,
                band=RiskBand.HIGH,
                reasons=(
                    DecisionReason(
                        code="NEW_RECIPIENT",
                        message="New recipient.",
                        contribution=0.15,
                    ),
                    DecisionReason(
                        code="VERY_HIGH_AMOUNT_DEVIATION",
                        message="High amount.",
                        contribution=0.20,
                    ),
                ),
            ),
        )

        self.assertEqual(
            result.question.code,
            "ACTIVE_PHONE_OR_CHAT",
        )

    def test_all_known_context_produces_no_question(self):
        context = ScamContext(
            phone_call=False,
            unknown_contact=False,
            urgency=False,
            reward_or_prize=False,
            support_impersonation=False,
            asked_to_keep_secret=False,
        )

        result = self.service.evaluate(
            transaction=self.make_transaction(),
            risk=self.make_risk(
                score=0.40,
                band=RiskBand.MEDIUM,
            ),
            context=context,
        )

        self.assertFalse(result.should_ask)
        self.assertIsNone(result.question)