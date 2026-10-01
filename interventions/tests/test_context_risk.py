from django.test import SimpleTestCase

from core.contracts import (
    DecisionReason,
    RiskAssessment,
    RiskBand,
    ScamContext,
)
from interventions.services.context_risk import (
    ContextRiskAdjuster,
)


class ContextRiskAdjusterTests(SimpleTestCase):
    def setUp(self):
        self.adjuster = ContextRiskAdjuster()

    def make_risk(
        self,
        *,
        score=0.30,
        band=RiskBand.MEDIUM,
    ):
        return RiskAssessment(
            score=score,
            band=band,
            reasons=(
                DecisionReason(
                    code="NEW_RECIPIENT",
                    message="New recipient.",
                    contribution=0.15,
                ),
                DecisionReason(
                    code="HIGH_AMOUNT_DEVIATION",
                    message="High amount deviation.",
                    contribution=0.15,
                ),
            ),
        )

    def test_empty_context_preserves_base_risk(self):
        adjusted = self.adjuster.adjust(
            risk=self.make_risk(),
            context=ScamContext(),
        )

        self.assertEqual(
            adjusted.score,
            0.30,
        )

        self.assertEqual(
            adjusted.band,
            RiskBand.MEDIUM,
        )

    def test_active_phone_context_increases_risk(self):
        adjusted = self.adjuster.adjust(
            risk=self.make_risk(),
            context=ScamContext(
                phone_call=True,
            ),
        )

        self.assertEqual(
            adjusted.score,
            0.50,
        )

        self.assertEqual(
            adjusted.band,
            RiskBand.HIGH,
        )

        reason_codes = {
            reason.code
            for reason in adjusted.reasons
        }

        self.assertIn(
            "CTX_ACTIVE_PHONE_OR_CHAT",
            reason_codes,
        )

    def test_impersonation_can_escalate_medium_to_high(self):
        adjusted = self.adjuster.adjust(
            risk=self.make_risk(),
            context=ScamContext(
                support_impersonation=True,
            ),
        )

        self.assertEqual(
            adjusted.score,
            0.55,
        )

        self.assertEqual(
            adjusted.band,
            RiskBand.HIGH,
        )

    def test_multiple_context_signals_can_reach_critical(self):
        adjusted = self.adjuster.adjust(
            risk=self.make_risk(),
            context=ScamContext(
                phone_call=True,
                urgency=True,
                reward_or_prize=True,
            ),
        )

        self.assertEqual(
            adjusted.score,
            0.80,
        )

        self.assertEqual(
            adjusted.band,
            RiskBand.CRITICAL,
        )

    def test_negative_answers_do_not_remove_existing_evidence(self):
        adjusted = self.adjuster.adjust(
            risk=self.make_risk(),
            context=ScamContext(
                phone_call=False,
                urgency=False,
                reward_or_prize=False,
                support_impersonation=False,
                asked_to_keep_secret=False,
            ),
        )

        self.assertEqual(
            adjusted.score,
            0.30,
        )

        self.assertEqual(
            adjusted.band,
            RiskBand.MEDIUM,
        )

    def test_score_is_capped_at_one(self):
        risk = RiskAssessment(
            score=0.85,
            band=RiskBand.CRITICAL,
            reasons=(
                DecisionReason(
                    code="BASE_HIGH_RISK",
                    message="Strong existing evidence.",
                    contribution=0.85,
                ),
            ),
        )

        adjusted = self.adjuster.adjust(
            risk=risk,
            context=ScamContext(
                phone_call=True,
                support_impersonation=True,
                asked_to_keep_secret=True,
            ),
        )

        self.assertEqual(
            adjusted.score,
            1.0,
        )

        self.assertEqual(
            adjusted.band,
            RiskBand.CRITICAL,
        )

    def test_adjustment_is_idempotent(self):
        context = ScamContext(
            phone_call=True,
            urgency=True,
        )

        first = self.adjuster.adjust(
            risk=self.make_risk(),
            context=context,
        )

        second = self.adjuster.adjust(
            risk=first,
            context=context,
        )

        self.assertEqual(
            first.score,
            second.score,
        )

        self.assertEqual(
            len(first.reasons),
            len(second.reasons),
        )