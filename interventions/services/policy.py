from dataclasses import dataclass

from core.contracts import (
    InterventionAction,
    NormalizedTransaction,
    RiskAssessment,
    RiskBand,
)


@dataclass(frozen=True, slots=True)
class InterventionProfile:
    action: InterventionAction
    protection_rate: float
    friction_cost: float
    operations_cost: float

    @property
    def intervention_cost(self) -> float:
        return (
            self.friction_cost
            + self.operations_cost
        )


@dataclass(frozen=True, slots=True)
class ActionEvaluation:
    action: InterventionAction
    protection_rate: float
    expected_residual_loss: float
    friction_cost: float
    operations_cost: float
    total_expected_cost: float


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    action: InterventionAction
    risk: RiskAssessment
    expected_fraud_exposure: float
    selected_cost: float
    reason: str
    evaluations: tuple[ActionEvaluation, ...]


class MinimumEffectiveInterventionPolicy:
    """
    Transparent intervention-selection baseline.

    The policy minimizes expected total harm:

        residual expected fraud loss
        + legitimate-user friction cost
        + operational cost

    Protection rates and cost values are prototype assumptions only.
    They are not claimed to represent measured upay intervention
    effectiveness or production economics.

    Real deployment would estimate these values through controlled
    experiments using governed operational data.
    """

    PROFILES = (
        InterventionProfile(
            action=InterventionAction.ALLOW,
            protection_rate=0.00,
            friction_cost=0.0,
            operations_cost=0.0,
        ),
        InterventionProfile(
            action=InterventionAction.CONTEXTUAL_WARNING,
            protection_rate=0.15,
            friction_cost=120.0,
            operations_cost=30.0,
        ),
        InterventionProfile(
            action=InterventionAction.SCAM_WARNING,
            protection_rate=0.30,
            friction_cost=250.0,
            operations_cost=50.0,
        ),
        InterventionProfile(
            action=InterventionAction.VERIFY,
            protection_rate=0.50,
            friction_cost=650.0,
            operations_cost=150.0,
        ),
        InterventionProfile(
            action=InterventionAction.COOLING_PERIOD,
            protection_rate=0.70,
            friction_cost=1200.0,
            operations_cost=300.0,
        ),
        InterventionProfile(
            action=InterventionAction.HUMAN_REVIEW,
            protection_rate=0.85,
            friction_cost=800.0,
            operations_cost=1200.0,
        ),
    )

    MIN_PROTECTION_BY_BAND = {
        RiskBand.LOW: 0.00,
        RiskBand.MEDIUM: 0.15,
        RiskBand.HIGH: 0.30,
        RiskBand.CRITICAL: 0.50,
    }

    def select(
        self,
        transaction: NormalizedTransaction,
        risk: RiskAssessment,
    ) -> PolicyDecision:
        expected_fraud_exposure = (
            risk.score
            * float(transaction.amount)
        )

        eligible_profiles = self._eligible_profiles(
            risk.band
        )

        evaluations = tuple(
            self._evaluate_action(
                profile=profile,
                expected_fraud_exposure=(
                    expected_fraud_exposure
                ),
            )
            for profile in eligible_profiles
        )

        selected = min(
            evaluations,
            key=lambda evaluation: (
                evaluation.total_expected_cost,
                evaluation.protection_rate,
            ),
        )

        return PolicyDecision(
            action=selected.action,
            risk=risk,
            expected_fraud_exposure=round(
                expected_fraud_exposure,
                2,
            ),
            selected_cost=selected.total_expected_cost,
            reason=self._decision_reason(
                selected=selected,
                risk=risk,
            ),
            evaluations=evaluations,
        )

    def _eligible_profiles(
        self,
        band: RiskBand,
    ) -> tuple[InterventionProfile, ...]:
        minimum_protection = (
            self.MIN_PROTECTION_BY_BAND[band]
        )

        if band == RiskBand.LOW:
            return tuple(
                profile
                for profile in self.PROFILES
                if profile.action
                in {
                    InterventionAction.ALLOW,
                    InterventionAction.CONTEXTUAL_WARNING,
                }
            )

        return tuple(
            profile
            for profile in self.PROFILES
            if profile.protection_rate
            >= minimum_protection
        )

    @staticmethod
    def _evaluate_action(
        *,
        profile: InterventionProfile,
        expected_fraud_exposure: float,
    ) -> ActionEvaluation:
        expected_residual_loss = (
            expected_fraud_exposure
            * (1.0 - profile.protection_rate)
        )

        total_expected_cost = (
            expected_residual_loss
            + profile.friction_cost
            + profile.operations_cost
        )

        return ActionEvaluation(
            action=profile.action,
            protection_rate=profile.protection_rate,
            expected_residual_loss=round(
                expected_residual_loss,
                2,
            ),
            friction_cost=profile.friction_cost,
            operations_cost=profile.operations_cost,
            total_expected_cost=round(
                total_expected_cost,
                2,
            ),
        )

    @staticmethod
    def _decision_reason(
        *,
        selected: ActionEvaluation,
        risk: RiskAssessment,
    ) -> str:
        return (
            f"{selected.action.value} has the lowest expected "
            f"total cost among interventions eligible for "
            f"{risk.band.value} risk under the current prototype "
            f"protection, friction, and operations assumptions."
        )