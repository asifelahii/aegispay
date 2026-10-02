from dataclasses import dataclass

from core.contracts import (
    InterventionAction,
)
from experiments.services.friction import (
    CustomerFrictionAccounting,
)
from experiments.services.runner import (
    AegisPayExperimentRunner,
    ExperimentResult,
    ExperimentSummary,
    ScenarioOutcome,
)
from experiments.services.scenario_generator import (
    GeneratedScenario,
)
from interventions.services.capacity import (
    HumanReviewCapacityAllocator,
    ReviewCandidate,
)
from interventions.services.policy import (
    MinimumEffectiveInterventionPolicy,
    PolicyDecision,
)
from interventions.services.decision import (
    AegisPayDecisionService,
)
from interventions.services.selective_context_probe import (
    DecisionRelevantContextProbeService,
)
from risk.services.rules import (
    RulesRiskEngine,
)


class NoContextProbeExperimentRunner:
    """
    AegisPay ablation with Context Probe removed.

    Preserved:
    - transaction features
    - behavioral risk
    - network risk
    - RulesRiskEngine
    - minimum-effective intervention policy
    - human-review capacity allocation
    - intervention-effect assumptions

    Removed:
    - Context Probe
    - context-risk adjustment

    Ground truth remains evaluation-only.
    """

    def __init__(
        self,
        risk_engine=None,
        intervention_policy=None,
        capacity_allocator=None,
    ):
        self.risk_engine = (
            risk_engine
            or RulesRiskEngine()
        )

        self.intervention_policy = (
            intervention_policy
            or MinimumEffectiveInterventionPolicy()
        )

        self.capacity_allocator = (
            capacity_allocator
            or HumanReviewCapacityAllocator()
        )

    def run(
        self,
        scenarios: list[
            GeneratedScenario
        ],
        *,
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

        review_candidates = []

        for scenario in scenarios:
            transaction = (
                scenario.transaction
            )

            base_risk = (
                self.risk_engine.assess(
                    transaction
                )
            )

            policy = (
                self.intervention_policy.select(
                    transaction=transaction,
                    risk=base_risk,
                )
            )

            decisions.append(
                (
                    scenario,
                    base_risk,
                    policy,
                )
            )

            review_candidates.append(
                ReviewCandidate(
                    transaction_id=(
                        transaction.transaction_id
                    ),
                    policy=policy,
                )
            )

        capacity_result = (
            self.capacity_allocator.allocate(
                review_candidates,
                capacity=review_capacity,
            )
        )

        allocation_by_id = {
            allocation.transaction_id: allocation
            for allocation
            in capacity_result.allocations
        }

        outcomes = []

        for (
            scenario,
            risk,
            policy,
        ) in decisions:
            transaction = (
                scenario.transaction
            )

            transaction_id = (
                transaction.transaction_id
            )

            allocation = (
                allocation_by_id[
                    transaction_id
                ]
            )

            evaluation = (
                self._evaluation_for_action(
                    policy=policy,
                    action=(
                        allocation.final_action
                    ),
                )
            )

            transaction_value = float(
                transaction.amount
            )

            if scenario.ground_truth.is_scam:
                prevented_scam_value = (
                    transaction_value
                    * evaluation.protection_rate
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
                    base_risk_score=(
                        risk.score
                    ),
                    final_risk_score=(
                        risk.score
                    ),
                    context_requested=False,
                    context_question_code=None,
                    requested_action=(
                        policy.action
                    ),
                    effective_action=(
                        allocation.final_action
                    ),
                    review_requested=(
                        allocation.original_action
                        == InterventionAction.HUMAN_REVIEW
                    ),
                    review_allocated=(
                        allocation.review_allocated
                    ),
                    transaction_value=round(
                        transaction_value,
                        2,
                    ),
                    protection_rate=(
                        evaluation.protection_rate
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
                        evaluation.friction_cost
                    ),
                    operations_cost=(
                        evaluation.operations_cost
                    ),
                )
            )

        summary = self._summarize(
            outcomes=outcomes,
            requested_reviews=(
                capacity_result.requested_reviews
            ),
            allocated_reviews=(
                capacity_result.allocated_reviews
            ),
        )

        return ExperimentResult(
            summary=summary,
            outcomes=tuple(outcomes),
        )

    @staticmethod
    def _evaluation_for_action(
        *,
        policy: PolicyDecision,
        action: InterventionAction,
    ):
        for evaluation in (
            policy.evaluations
        ):
            if (
                evaluation.action
                == action
            ):
                return evaluation

        raise ValueError(
            f"No evaluation found for "
            f"{action.value}."
        )

    @staticmethod
    def _summarize(
        *,
        outcomes: list[
            ScenarioOutcome
        ],
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
                    for outcome
                    in scam_outcomes
                ),
                2,
            ),
            prevented_scam_value=round(
                sum(
                    outcome.prevented_scam_value
                    for outcome
                    in scam_outcomes
                ),
                2,
            ),
            residual_scam_loss=round(
                sum(
                    outcome.residual_scam_loss
                    for outcome
                    in scam_outcomes
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
                    for outcome
                    in outcomes
                ),
                2,
            ),
        )

    @staticmethod
    def _validate_scenarios(
        scenarios: list[
            GeneratedScenario
        ],
    ):
        transaction_ids = [
            scenario.transaction.transaction_id
            for scenario in scenarios
        ]

        if (
            len(transaction_ids)
            != len(set(transaction_ids))
        ):
            raise ValueError(
                "Ablation experiment transaction IDs "
                "must be unique."
            )


@dataclass(frozen=True, slots=True)
class ContextProbeAblationMetrics:
    strategy: str

    prevention_rate: float
    prevented_scam_value: float
    residual_scam_loss: float

    context_probes: int

    legitimate_intervention_friction: float
    legitimate_probe_friction: float
    legitimate_total_friction: float

    requested_reviews: int
    allocated_reviews: int

    operations_cost: float
    total_modeled_cost: float


@dataclass(frozen=True, slots=True)
class ContextProbeAblationResult:
    review_capacity: int
    strategies: tuple[
        ContextProbeAblationMetrics,
        ...
    ]


class ContextProbeAblationService:
    WITHOUT_PROBE = (
        "AEGISPAY_NO_CONTEXT_PROBE"
    )

    FULL = "AEGISPAY"

    def __init__(
        self,
        no_probe_runner=None,
        full_runner=None,
        friction_accounting=None,
    ):
        self.no_probe_runner = (
            no_probe_runner
            or NoContextProbeExperimentRunner()
        )

        self.full_runner = (
            full_runner
            or AegisPayExperimentRunner(
                decision_service=AegisPayDecisionService(
                    context_probe=(
                        DecisionRelevantContextProbeService()
                    )
                )
            )
        )

        self.friction_accounting = (
            friction_accounting
            or CustomerFrictionAccounting()
        )

    def compare(
        self,
        scenarios: list[
            GeneratedScenario
        ],
        *,
        review_capacity: int,
    ) -> ContextProbeAblationResult:
        if review_capacity < 0:
            raise ValueError(
                "Review capacity cannot be negative."
            )

        no_probe = (
            self.no_probe_runner.run(
                scenarios,
                review_capacity=review_capacity,
            )
        )

        full = (
            self.full_runner.run(
                scenarios,
                review_capacity=review_capacity,
            )
        )

        return ContextProbeAblationResult(
            review_capacity=review_capacity,
            strategies=(
                self._metrics(
                    strategy=(
                        self.WITHOUT_PROBE
                    ),
                    result=no_probe,
                ),
                self._metrics(
                    strategy=self.FULL,
                    result=full,
                ),
            ),
        )

    def _metrics(
        self,
        *,
        strategy: str,
        result: ExperimentResult,
    ) -> ContextProbeAblationMetrics:
        summary = result.summary

        friction = (
            self.friction_accounting.calculate(
                result
            )
        )

        if summary.total_scam_value > 0:
            prevention_rate = (
                summary.prevented_scam_value
                / summary.total_scam_value
            )
        else:
            prevention_rate = 0.0

        total_modeled_cost = (
            summary.residual_scam_loss
            + friction.legitimate_total_customer_friction_cost
            + summary.operations_cost
        )

        return ContextProbeAblationMetrics(
            strategy=strategy,
            prevention_rate=round(
                prevention_rate,
                4,
            ),
            prevented_scam_value=(
                summary.prevented_scam_value
            ),
            residual_scam_loss=(
                summary.residual_scam_loss
            ),
            context_probes=(
                summary.context_probes
            ),
            legitimate_intervention_friction=(
                friction.legitimate_intervention_friction_cost
            ),
            legitimate_probe_friction=(
                friction.legitimate_context_probe_friction_cost
            ),
            legitimate_total_friction=(
                friction.legitimate_total_customer_friction_cost
            ),
            requested_reviews=(
                summary.requested_reviews
            ),
            allocated_reviews=(
                summary.allocated_reviews
            ),
            operations_cost=(
                summary.operations_cost
            ),
            total_modeled_cost=round(
                total_modeled_cost,
                2,
            ),
        )