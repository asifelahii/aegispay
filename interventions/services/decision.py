from dataclasses import dataclass
from enum import StrEnum

from core.contracts import (
    ContextQuestion,
    NormalizedTransaction,
    RiskAssessment,
    ScamContext,
)
from interventions.services.selective_context_probe import (
    DecisionRelevantContextProbeService,
)
from interventions.services.context_risk import (
    ContextRiskAdjuster,
)
from interventions.services.policy import (
    MinimumEffectiveInterventionPolicy,
    PolicyDecision,
)


class DecisionStatus(StrEnum):
    NEEDS_CONTEXT = "NEEDS_CONTEXT"
    DECIDED = "DECIDED"


@dataclass(frozen=True, slots=True)
class AegisPayDecision:
    status: DecisionStatus
    transaction: NormalizedTransaction
    base_risk: RiskAssessment
    final_risk: RiskAssessment
    context_question: ContextQuestion | None
    policy: PolicyDecision | None


class AegisPayDecisionService:
    """
    Coordinates AegisPay's runtime decision workflow.

    Canonical prototype behavior:

    1. Start with transaction and base risk.
    2. If no customer context has been supplied, determine whether
       one targeted context question is worth asking.
    3. If a question is required, stop and return NEEDS_CONTEXT.
    4. If context is supplied, incorporate it into the risk state.
    5. Select the minimum-effective intervention.

    In v0, at most one context-probe interaction occurs before the
    intervention decision. The default Context Probe is the
    decision-relevant policy; the legacy heuristic remains available
    through explicit dependency injection. This avoids unnecessary repeated friction.
    """

    def __init__(
        self,
        context_probe=None,
        context_risk_adjuster=None,
        intervention_policy=None,
    ):
        self.context_probe = context_probe or (
            DecisionRelevantContextProbeService()
        )

        self.context_risk_adjuster = (
            context_risk_adjuster
            or ContextRiskAdjuster()
        )

        self.intervention_policy = (
            intervention_policy
            or MinimumEffectiveInterventionPolicy()
        )

    def decide(
        self,
        *,
        transaction: NormalizedTransaction,
        base_risk: RiskAssessment,
        context: ScamContext | None = None,
    ) -> AegisPayDecision:
        if context is None:
            probe = self.context_probe.evaluate(
                transaction=transaction,
                risk=base_risk,
            )

            if probe.should_ask:
                return AegisPayDecision(
                    status=DecisionStatus.NEEDS_CONTEXT,
                    transaction=transaction,
                    base_risk=base_risk,
                    final_risk=base_risk,
                    context_question=probe.question,
                    policy=None,
                )

            policy = self.intervention_policy.select(
                transaction=transaction,
                risk=base_risk,
            )

            return AegisPayDecision(
                status=DecisionStatus.DECIDED,
                transaction=transaction,
                base_risk=base_risk,
                final_risk=base_risk,
                context_question=None,
                policy=policy,
            )

        adjusted_risk = (
            self.context_risk_adjuster.adjust(
                risk=base_risk,
                context=context,
            )
        )

        policy = self.intervention_policy.select(
            transaction=transaction,
            risk=adjusted_risk,
        )

        return AegisPayDecision(
            status=DecisionStatus.DECIDED,
            transaction=transaction,
            base_risk=base_risk,
            final_risk=adjusted_risk,
            context_question=None,
            policy=policy,
        )