from dataclasses import dataclass

from core.contracts import (
    ContextQuestion,
    NormalizedTransaction,
    RiskAssessment,
    RiskBand,
    ScamContext,
)


@dataclass(frozen=True, slots=True)
class ContextProbeResult:
    should_ask: bool
    question: ContextQuestion | None
    reason: str
    priority_score: float = 0.0


class ContextProbeService:
    """
    Selectively asks for one piece of scam context when transaction
    evidence is concerning but not yet decisive.

    This is a transparent prototype policy, not a learned model.

    The important behavior is selective acquisition:
    low-risk transactions should not receive unnecessary friction,
    while ambiguous medium/high-risk situations may justify one
    targeted question.

    CRITICAL transactions do not require an additional probe in this
    baseline because existing evidence is already strong enough to
    proceed to intervention selection.
    """

    QUESTIONS = {
        "phone_call": ContextQuestion(
            code="ACTIVE_PHONE_OR_CHAT",
            prompt=(
                "Is someone currently on a phone call or chat "
                "asking you to send this money?"
            ),
            answer_key="phone_call",
        ),
        "reward_or_prize": ContextQuestion(
            code="PROMISED_BENEFIT",
            prompt=(
                "Are you being asked to make this payment to receive "
                "a prize, loan, job, refund, investment return, or "
                "other promised benefit?"
            ),
            answer_key="reward_or_prize",
        ),
        "support_impersonation": ContextQuestion(
            code="SUPPORT_IMPERSONATION",
            prompt=(
                "Does the recipient or person guiding this payment "
                "claim to work for upay, UCB, a bank, or another "
                "financial institution?"
            ),
            answer_key="support_impersonation",
        ),
        "asked_to_keep_secret": ContextQuestion(
            code="SECRECY_REQUEST",
            prompt=(
                "Has anyone told you not to discuss this payment "
                "with family, the financial service, or authorities?"
            ),
            answer_key="asked_to_keep_secret",
        ),
    }

    def evaluate(
        self,
        transaction: NormalizedTransaction,
        risk: RiskAssessment,
        context: ScamContext | None = None,
    ) -> ContextProbeResult:
        context = context or ScamContext()

        if risk.band == RiskBand.LOW:
            return ContextProbeResult(
                should_ask=False,
                question=None,
                reason=(
                    "Existing evidence is low risk; additional "
                    "customer friction is not justified."
                ),
            )

        if risk.band == RiskBand.CRITICAL:
            return ContextProbeResult(
                should_ask=False,
                question=None,
                reason=(
                    "Existing evidence is already critical; "
                    "additional context is not required before "
                    "intervention selection."
                ),
            )

        candidates = self._candidate_questions(
            transaction=transaction,
            risk=risk,
            context=context,
        )

        if not candidates:
            return ContextProbeResult(
                should_ask=False,
                question=None,
                reason=(
                    "No unanswered context question is expected "
                    "to materially improve the current decision."
                ),
            )

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        priority_score, question, selection_reason = candidates[0]

        return ContextProbeResult(
            should_ask=True,
            question=question,
            reason=selection_reason,
            priority_score=round(priority_score, 4),
        )

    def _candidate_questions(
        self,
        *,
        transaction: NormalizedTransaction,
        risk: RiskAssessment,
        context: ScamContext,
    ) -> list[tuple[float, ContextQuestion, str]]:
        candidates = []

        reason_codes = {
            reason.code
            for reason in risk.reasons
        }

        if context.phone_call is None:
            score = 0.40

            if "NEW_RECIPIENT" in reason_codes:
                score += 0.20

            if (
                "VERY_HIGH_AMOUNT_DEVIATION" in reason_codes
                or "HIGH_AMOUNT_DEVIATION" in reason_codes
            ):
                score += 0.15

            candidates.append(
                (
                    score,
                    self.QUESTIONS["phone_call"],
                    (
                        "A new or unusual payment can be consistent "
                        "with social-engineering pressure, so active "
                        "call/chat context may change the intervention."
                    ),
                )
            )

        if context.support_impersonation is None:
            score = 0.30

            if transaction.is_new_recipient:
                score += 0.15

            if transaction.device_changed_recently:
                score += 0.10

            candidates.append(
                (
                    score,
                    self.QUESTIONS["support_impersonation"],
                    (
                        "Impersonation context may distinguish a "
                        "legitimate unusual payment from a scam."
                    ),
                )
            )

        if context.reward_or_prize is None:
            score = 0.25

            if (
                "VERY_HIGH_AMOUNT_DEVIATION" in reason_codes
                or "ABOVE_SENDER_P95" in reason_codes
            ):
                score += 0.20

            candidates.append(
                (
                    score,
                    self.QUESTIONS["reward_or_prize"],
                    (
                        "A promised benefit may indicate an "
                        "advance-fee or reward-related scam."
                    ),
                )
            )

        if context.asked_to_keep_secret is None:
            score = 0.20

            if "HIGH_RECIPIENT_FAN_IN" in reason_codes:
                score += 0.15

            if "RAPID_CASHOUT" in reason_codes:
                score += 0.15

            candidates.append(
                (
                    score,
                    self.QUESTIONS["asked_to_keep_secret"],
                    (
                        "Secrecy pressure can add useful scam context "
                        "when beneficiary behavior is suspicious."
                    ),
                )
            )

        return candidates