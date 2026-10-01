from datetime import UTC, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from core.contracts import (
    DecisionReason,
    NormalizedTransaction,
    RiskAssessment,
    RiskBand,
    TransactionType,
)
from interventions.services.selective_context_probe import (
    DecisionRelevantContextProbeService,
)


class DecisionRelevantContextProbeServiceTests(
    SimpleTestCase
):
    def setUp(self):
        self.service = (
            DecisionRelevantContextProbeService()
        )

    def make_transaction(
        self,
        **overrides,
    ):
        data = {
            "transaction_id": "TX-001",
            "sender_id": "CUS-001",
            "recipient_id": "CUS-002",
            "amount": Decimal("5000.00"),
            "transaction_type": (
                TransactionType.P2P
            ),
            "occurred_at": datetime.now(
                UTC
            ),
        }

        data.update(
            overrides
        )

        return NormalizedTransaction(
            **data
        )

    def make_reason(
        self,
        code,
        contribution,
    ):
        return DecisionReason(
            code=code,
            message=code,
            contribution=contribution,
        )

    def make_risk(
        self,
        *,
        score,
        band,
        reasons,
    ):
        return RiskAssessment(
            score=score,
            band=band,
            reasons=tuple(reasons),
        )

    def test_low_risk_is_not_probed(
        self,
    ):
        result = self.service.evaluate(
            transaction=(
                self.make_transaction()
            ),
            risk=self.make_risk(
                score=0.10,
                band=RiskBand.LOW,
                reasons=[],
            ),
        )

        self.assertFalse(
            result.should_ask
        )

    def test_critical_risk_is_not_probed(
        self,
    ):
        result = self.service.evaluate(
            transaction=(
                self.make_transaction()
            ),
            risk=self.make_risk(
                score=0.80,
                band=RiskBand.CRITICAL,
                reasons=[],
            ),
        )

        self.assertFalse(
            result.should_ask
        )

    def test_new_recipient_amount_pattern_routes_to_phone(
        self,
    ):
        result = self.service.evaluate(
            transaction=self.make_transaction(
                amount=Decimal("3000.00"),
                is_new_recipient=True,
            ),
            risk=self.make_risk(
                score=0.25,
                band=RiskBand.MEDIUM,
                reasons=[
                    self.make_reason(
                        "NEW_RECIPIENT",
                        0.15,
                    ),
                    self.make_reason(
                        "HIGH_AMOUNT_DEVIATION",
                        0.10,
                    ),
                ],
            ),
        )

        self.assertTrue(
            result.should_ask
        )

        self.assertEqual(
            result.question.code,
            "ACTIVE_PHONE_OR_CHAT",
        )

    def test_above_p95_pattern_prioritizes_promised_benefit(
        self,
    ):
        result = self.service.evaluate(
            transaction=self.make_transaction(
                is_new_recipient=True,
            ),
            risk=self.make_risk(
                score=0.35,
                band=RiskBand.MEDIUM,
                reasons=[
                    self.make_reason(
                        "NEW_RECIPIENT",
                        0.15,
                    ),
                    self.make_reason(
                        "HIGH_AMOUNT_DEVIATION",
                        0.10,
                    ),
                    self.make_reason(
                        "ABOVE_SENDER_P95",
                        0.10,
                    ),
                ],
            ),
        )

        self.assertTrue(
            result.should_ask
        )

        self.assertEqual(
            result.question.code,
            "PROMISED_BENEFIT",
        )

    def test_network_pattern_routes_to_secrecy(
        self,
    ):
        result = self.service.evaluate(
            transaction=(
                self.make_transaction()
            ),
            risk=self.make_risk(
                score=0.40,
                band=RiskBand.MEDIUM,
                reasons=[
                    self.make_reason(
                        "HIGH_RECIPIENT_FAN_IN",
                        0.10,
                    ),
                    self.make_reason(
                        "HIGH_PASS_THROUGH",
                        0.15,
                    ),
                    self.make_reason(
                        "RAPID_CASHOUT",
                        0.15,
                    ),
                ],
            ),
        )

        self.assertTrue(
            result.should_ask
        )

        self.assertEqual(
            result.question.code,
            "SECRECY_REQUEST",
        )

    def test_device_change_routes_to_support_impersonation(
        self,
    ):
        result = self.service.evaluate(
            transaction=self.make_transaction(
                device_changed_recently=True,
            ),
            risk=self.make_risk(
                score=0.30,
                band=RiskBand.MEDIUM,
                reasons=[
                    self.make_reason(
                        "RECENT_DEVICE_CHANGE",
                        0.15,
                    ),
                    self.make_reason(
                        "NEW_RECIPIENT",
                        0.15,
                    ),
                ],
            ),
        )

        self.assertTrue(
            result.should_ask
        )

        self.assertEqual(
            result.question.code,
            "SUPPORT_IMPERSONATION",
        )

    def test_probe_is_skipped_when_positive_answer_cannot_change_action(
        self,
    ):
        result = self.service.evaluate(
            transaction=self.make_transaction(
                amount=Decimal("500.00"),
                is_new_recipient=True,
            ),
            risk=self.make_risk(
                score=0.25,
                band=RiskBand.MEDIUM,
                reasons=[
                    self.make_reason(
                        "NEW_RECIPIENT",
                        0.15,
                    ),
                    self.make_reason(
                        "HIGH_AMOUNT_DEVIATION",
                        0.10,
                    ),
                ],
            ),
        )

        self.assertFalse(
            result.should_ask
        )