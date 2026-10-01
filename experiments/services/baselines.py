from enum import StrEnum

from core.contracts import (
    InterventionAction,
    RiskAssessment,
    RiskBand,
)
from experiments.services.runner import (
    ExperimentResult,
    ExperimentSummary,
    ScenarioOutcome,
)
from experiments.services.scenario_generator import (
    GeneratedScenario,
)
from interventions.services.policy import (
    InterventionProfile,
    MinimumEffectiveInterventionPolicy,
)
from risk.services.rules import RulesRiskEngine


class BaselineStrategy(StrEnum):
    NO_INTERVENTION = "NO_INTERVENTION"
    HARD_THRESHOLD = "HARD_THRESHOLD"
    STATIC_TIER = "STATIC_TIER"


class BaselineExperimentRunner:
    """
    Runs conventional comparison policies against the same scenarios
    used by the full AegisPay experiment.

    Runtime decisions use transaction-derived risk only.

    Ground truth is used only after the action has been selected when
    calculating experiment metrics.

    Baselines intentionally receive no scam-context information.
    """

    HARD_THRESHOLD = 0.50

    STATIC_TIER_ACTIONS = {
        RiskBand.LOW: InterventionAction.ALLOW,
        RiskBand.MEDIUM: (
            InterventionAction.CONTEXTUAL_WARNING
        ),
        RiskBand.HIGH: InterventionAction.VERIFY,
        RiskBand.CRITICAL: (
            InterventionAction.HUMAN_REVIEW
        ),
    }

    REVIEW_FALLBACK = InterventionAction.VERIFY

    def __init__(
        self,
        risk_engine=None,
    ):
        self.risk_engine = (
            risk_engine
            or RulesRiskEngine()
        )

        self.profiles = {
            profile.action: profile
            for profile
            in MinimumEffectiveInterventionPolicy.PROFILES
        }

    def run(
        self,
        scenarios: list[GeneratedScenario],
        *,
        strategy: BaselineStrategy,
        review_capacity: int,
    ) -> ExperimentResult:
        if review_capacity < 0:
            raise ValueError(
                "Review capacity cannot be negative."
            )

        self._validate_scenarios(
            scenarios
        )

        decisions = []

        review_requests = []

        for scenario in scenarios:
            transaction = scenario.transaction

            risk = self.risk_engine.assess(
                transaction
            )

            requested_action = (
                self._select_action(
                    strategy=strategy,
                    risk=risk,
                )
            )

            transaction_id = (
                transaction.transaction_id
            )

            decisions.append(
                (
                    scenario,
                    risk,
                    requested_action,
                )
            )

            if (
                requested_action
                == InterventionAction.HUMAN_REVIEW
            ):
                expected_exposure = (
                    risk.score
                    * float(transaction.amount)
                )

                review_requests.append(
                    (
                        expected_exposure,
                        transaction_id,
                    )
                )

        review_requests.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        allocated_review_ids = {
            transaction_id
            for (
                expected_exposure,
                transaction_id,
            )
            in review_requests[:review_capacity]
        }

        outcomes = []

        for (
            scenario,
            risk,
            requested_action,
        ) in decisions:
            transaction = scenario.transaction

            transaction_id = (
                transaction.transaction_id
            )

            review_requested = (
                requested_action
                == InterventionAction.HUMAN_REVIEW
            )

            review_allocated = (
                review_requested
                and transaction_id
                in allocated_review_ids
            )

            if (
                review_requested
                and not review_allocated
            ):
                effective_action = (
                    self.REVIEW_FALLBACK
                )
            else:
                effective_action = (
                    requested_action
                )

            profile = self._profile_for_action(
                effective_action
            )

            transaction_value = float(
                transaction.amount
            )

            if scenario.ground_truth.is_scam:
                prevented_scam_value = (
                    transaction_value
                    * profile.protection_rate
                )

                residual_scam_loss = (
                    transaction_value
                    - prevented_scam_value
                )

            else:
                prevented_scam_value = 0.0
                residual_scam_loss = 0.0

            outcomes.append(
                ScenarioOutcome(
                    transaction_id=transaction_id,
                    scenario_type=(
                        scenario.scenario_type.value
                    ),
                    is_scam=(
                        scenario.ground_truth.is_scam
                    ),
                    base_risk_score=risk.score,
                    final_risk_score=risk.score,
                    context_requested=False,
                    context_question_code=None,
                    requested_action=requested_action,
                    effective_action=effective_action,
                    review_requested=review_requested,
                    review_allocated=review_allocated,
                    transaction_value=round(
                        transaction_value,
                        2,
                    ),
                    protection_rate=(
                        profile.protection_rate
                    ),
                    prevented_scam_value=round(
                        prevented_scam_value,
                        2,
                    ),
                    residual_scam_loss=round(
                        residual_scam_loss,
                        2,
                    ),
                    friction_cost=(
                        profile.friction_cost
                    ),
                    operations_cost=(
                        profile.operations_cost
                    ),
                )
            )

        summary = self._summarize(
            outcomes,
            requested_reviews=len(
                review_requests
            ),
            allocated_reviews=len(
                allocated_review_ids
            ),
        )

        return ExperimentResult(
            summary=summary,
            outcomes=tuple(outcomes),
        )

    def _select_action(
        self,
        *,
        strategy: BaselineStrategy,
        risk: RiskAssessment,
    ) -> InterventionAction:
        if (
            strategy
            == BaselineStrategy.NO_INTERVENTION
        ):
            return InterventionAction.ALLOW

        if (
            strategy
            == BaselineStrategy.HARD_THRESHOLD
        ):
            if (
                risk.score
                >= self.HARD_THRESHOLD
            ):
                return (
                    InterventionAction.HUMAN_REVIEW
                )

            return InterventionAction.ALLOW

        if (
            strategy
            == BaselineStrategy.STATIC_TIER
        ):
            return self.STATIC_TIER_ACTIONS[
                risk.band
            ]

        raise ValueError(
            f"Unsupported baseline strategy: "
            f"{strategy}"
        )

    def _profile_for_action(
        self,
        action: InterventionAction,
    ) -> InterventionProfile:
        try:
            return self.profiles[action]
        except KeyError as error:
            raise ValueError(
                f"No intervention profile exists "
                f"for {action.value}."
            ) from error

    @staticmethod
    def _summarize(
        outcomes: list[ScenarioOutcome],
        *,
        requested_reviews: int,
        allocated_reviews: int,
    ) -> ExperimentSummary:
        scam_outcomes = [
            outcome
            for outcome in outcomes
            if outcome.is_scam
        ]

        legitimate_outcomes = [
            outcome
            for outcome in outcomes
            if not outcome.is_scam
        ]

        return ExperimentSummary(
            total_scenarios=len(
                outcomes
            ),
            scam_scenarios=len(
                scam_outcomes
            ),
            legitimate_scenarios=len(
                legitimate_outcomes
            ),
            context_probes=0,
            requested_reviews=(
                requested_reviews
            ),
            allocated_reviews=(
                allocated_reviews
            ),
            total_scam_value=round(
                sum(
                    outcome.transaction_value
                    for outcome in scam_outcomes
                ),
                2,
            ),
            prevented_scam_value=round(
                sum(
                    outcome.prevented_scam_value
                    for outcome in scam_outcomes
                ),
                2,
            ),
            residual_scam_loss=round(
                sum(
                    outcome.residual_scam_loss
                    for outcome in scam_outcomes
                ),
                2,
            ),
            legitimate_friction_cost=round(
                sum(
                    outcome.friction_cost
                    for outcome
                    in legitimate_outcomes
                ),
                2,
            ),
            operations_cost=round(
                sum(
                    outcome.operations_cost
                    for outcome in outcomes
                ),
                2,
            ),
        )

    @staticmethod
    def _validate_scenarios(
        scenarios: list[
            GeneratedScenario
        ],
    ) -> None:
        transaction_ids = [
            scenario.transaction.transaction_id
            for scenario in scenarios
        ]

        if (
            len(transaction_ids)
            != len(set(transaction_ids))
        ):
            raise ValueError(
                "Baseline experiment transaction IDs "
                "must be unique."
            )