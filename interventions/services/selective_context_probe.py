from dataclasses import replace

from core.contracts import (
    NormalizedTransaction,
    RiskAssessment,
    RiskBand,
    ScamContext,
)
from interventions.services.context_probe import (
    ContextProbeResult,
    ContextProbeService,
)
from interventions.services.context_risk import (
    ContextRiskAdjuster,
)
from interventions.services.policy import (
    MinimumEffectiveInterventionPolicy,
)


class DecisionRelevantContextProbeService:
    """
    Candidate selective Context Probe policy.

    This service uses only information available at runtime.

    It does not use:
    - scenario type
    - scam ground truth
    - hidden synthetic context
    - evaluation labels

    A question must satisfy two conditions:

    1. Its topic must be relevant to the observed risk evidence.
    2. A hypothetical positive answer must be capable of changing
       the requested intervention under the current policy.

    This is a decision-relevance heuristic, not a learned model and
    not a full probabilistic value-of-information implementation.
    """

    QUESTIONS = ContextProbeService.QUESTIONS

    def __init__(
        self,
        context_risk_adjuster=None,
        intervention_policy=None,
    ):
        self.context_risk_adjuster = (
            context_risk_adjuster
            or ContextRiskAdjuster()
        )

        self.intervention_policy = (
            intervention_policy
            or MinimumEffectiveInterventionPolicy()
        )

    def evaluate(
        self,
        transaction: NormalizedTransaction,
        risk: RiskAssessment,
        context: ScamContext | None = None,
    ) -> ContextProbeResult:
        context = (
            context
            or ScamContext()
        )

        if risk.band == RiskBand.LOW:
            return ContextProbeResult(
                should_ask=False,
                question=None,
                reason=(
                    "Existing evidence is low risk; "
                    "additional customer friction is "
                    "not justified."
                ),
            )

        if risk.band == RiskBand.CRITICAL:
            return ContextProbeResult(
                should_ask=False,
                question=None,
                reason=(
                    "Existing evidence is already critical; "
                    "additional context is not required "
                    "before intervention selection."
                ),
            )

        candidates = (
            self._evidence_candidates(
                transaction=transaction,
                risk=risk,
                context=context,
            )
        )

        if not candidates:
            return ContextProbeResult(
                should_ask=False,
                question=None,
                reason=(
                    "No unanswered question is strongly "
                    "matched to the observed risk evidence."
                ),
            )

        base_policy = (
            self.intervention_policy.select(
                transaction=transaction,
                risk=risk,
            )
        )

        decision_relevant = []

        for (
            priority,
            question,
            selection_reason,
        ) in candidates:
            positive_context = replace(
                context,
                **{
                    question.answer_key: True
                },
            )

            positive_risk = (
                self.context_risk_adjuster.adjust(
                    risk=risk,
                    context=positive_context,
                )
            )

            positive_policy = (
                self.intervention_policy.select(
                    transaction=transaction,
                    risk=positive_risk,
                )
            )

            if (
                positive_policy.action
                == base_policy.action
            ):
                continue

            decision_relevant.append(
                (
                    priority,
                    question,
                    selection_reason,
                )
            )

        if not decision_relevant:
            return ContextProbeResult(
                should_ask=False,
                question=None,
                reason=(
                    "A positive answer to the available "
                    "context questions would not change "
                    "the requested intervention."
                ),
            )

        decision_relevant.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        (
            priority,
            question,
            selection_reason,
        ) = decision_relevant[0]

        return ContextProbeResult(
            should_ask=True,
            question=question,
            reason=selection_reason,
            priority_score=round(
                priority,
                4,
            ),
        )

    def _evidence_candidates(
        self,
        *,
        transaction: NormalizedTransaction,
        risk: RiskAssessment,
        context: ScamContext,
    ):
        reason_codes = {
            reason.code
            for reason in risk.reasons
        }

        candidates = []

        amount_deviation = bool(
            {
                "HIGH_AMOUNT_DEVIATION",
                "VERY_HIGH_AMOUNT_DEVIATION",
            }
            & reason_codes
        )

        network_signal = bool(
            {
                "HIGH_RECIPIENT_FAN_IN",
                "HIGH_PASS_THROUGH",
                "RAPID_CASHOUT",
            }
            & reason_codes
        )

        # Device-change evidence is most directly routed toward
        # impersonation/support verification.
        if (
            context.support_impersonation
            is None
            and "RECENT_DEVICE_CHANGE"
            in reason_codes
        ):
            candidates.append(
                (
                    0.95,
                    self.QUESTIONS[
                        "support_impersonation"
                    ],
                    (
                        "Recent device-change evidence makes "
                        "support or institution impersonation "
                        "context decision-relevant."
                    ),
                )
            )

        # Suspicious recipient-network behavior is routed toward
        # secrecy/coercion context rather than the generic phone
        # question.
        if (
            context.asked_to_keep_secret
            is None
            and network_signal
        ):
            score = 0.80

            if (
                "HIGH_RECIPIENT_FAN_IN"
                in reason_codes
            ):
                score += 0.05

            if (
                "HIGH_PASS_THROUGH"
                in reason_codes
            ):
                score += 0.05

            if (
                "RAPID_CASHOUT"
                in reason_codes
            ):
                score += 0.10

            candidates.append(
                (
                    score,
                    self.QUESTIONS[
                        "asked_to_keep_secret"
                    ],
                    (
                        "Suspicious beneficiary movement "
                        "makes secrecy or coercion context "
                        "more relevant than a generic probe."
                    ),
                )
            )

        # Very unusual high-value payments are routed toward
        # advance-fee / promised-benefit context.
        if (
            context.reward_or_prize
            is None
            and amount_deviation
            and "ABOVE_SENDER_P95"
            in reason_codes
        ):
            candidates.append(
                (
                    0.85,
                    self.QUESTIONS[
                        "reward_or_prize"
                    ],
                    (
                        "A payment above the sender's "
                        "historical high-value range makes "
                        "promised-benefit context relevant."
                    ),
                )
            )

        # A new recipient plus unusual amount is a reasonable
        # social-engineering pattern for active call/chat context.
        if (
            context.phone_call
            is None
            and "NEW_RECIPIENT"
            in reason_codes
            and amount_deviation
        ):
            candidates.append(
                (
                    0.80,
                    self.QUESTIONS[
                        "phone_call"
                    ],
                    (
                        "A new recipient combined with an "
                        "unusual amount can indicate an "
                        "actively guided payment."
                    ),
                )
            )

        return candidates