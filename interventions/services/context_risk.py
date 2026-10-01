from core.contracts import (
    DecisionReason,
    RiskAssessment,
    RiskBand,
    ScamContext,
)


class ContextRiskAdjuster:
    """
    Adds structured scam-context evidence to an existing risk assessment.

    This is a transparent prototype baseline, not a learned model.

    Positive scam-context indicators may increase risk.
    Negative answers do not remove transaction, behavioral, or
    network evidence in v0.

    The adjustment is idempotent: applying the same context more than
    once does not repeatedly add the same context contribution.
    """

    CONTEXT_PREFIX = "CTX_"

    def adjust(
        self,
        risk: RiskAssessment,
        context: ScamContext,
    ) -> RiskAssessment:
        base_reasons = tuple(
            reason
            for reason in risk.reasons
            if not reason.code.startswith(
                self.CONTEXT_PREFIX
            )
        )

        base_score = sum(
            reason.contribution
            for reason in base_reasons
        )

        context_reasons = self._context_reasons(
            context
        )

        context_score = sum(
            reason.contribution
            for reason in context_reasons
        )

        score = min(
            1.0,
            base_score + context_score,
        )

        reasons = (
            base_reasons
            + tuple(context_reasons)
        )

        return RiskAssessment(
            score=round(score, 4),
            band=self._risk_band(score),
            reasons=reasons,
        )

    @staticmethod
    def _context_reasons(
        context: ScamContext,
    ) -> list[DecisionReason]:
        reasons = []

        if context.phone_call is True:
            reasons.append(
                DecisionReason(
                    code="CTX_ACTIVE_PHONE_OR_CHAT",
                    message=(
                        "The customer reports that someone is "
                        "actively guiding the payment by call or chat."
                    ),
                    contribution=0.20,
                )
            )

        if context.unknown_contact is True:
            reasons.append(
                DecisionReason(
                    code="CTX_UNKNOWN_CONTACT",
                    message=(
                        "The customer is interacting with an "
                        "unknown or untrusted contact."
                    ),
                    contribution=0.10,
                )
            )

        if context.urgency is True:
            reasons.append(
                DecisionReason(
                    code="CTX_URGENCY_PRESSURE",
                    message=(
                        "The customer reports pressure to complete "
                        "the payment urgently."
                    ),
                    contribution=0.10,
                )
            )

        if context.reward_or_prize is True:
            reasons.append(
                DecisionReason(
                    code="CTX_PROMISED_BENEFIT",
                    message=(
                        "The payment is connected to a promised "
                        "prize, loan, job, refund, investment return, "
                        "or similar benefit."
                    ),
                    contribution=0.20,
                )
            )

        if context.support_impersonation is True:
            reasons.append(
                DecisionReason(
                    code="CTX_SUPPORT_IMPERSONATION",
                    message=(
                        "Someone involved in the payment claims to "
                        "represent a financial institution or service."
                    ),
                    contribution=0.25,
                )
            )

        if context.asked_to_keep_secret is True:
            reasons.append(
                DecisionReason(
                    code="CTX_SECRECY_REQUEST",
                    message=(
                        "The customer reports being told to keep "
                        "the payment secret."
                    ),
                    contribution=0.20,
                )
            )

        return reasons

    @staticmethod
    def _risk_band(
        score: float,
    ) -> RiskBand:
        if score >= 0.75:
            return RiskBand.CRITICAL

        if score >= 0.50:
            return RiskBand.HIGH

        if score >= 0.25:
            return RiskBand.MEDIUM

        return RiskBand.LOW