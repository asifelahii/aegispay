from dataclasses import dataclass

from core.contracts import (
    InterventionAction,
    ScamContext,
)
from experiments.services.scenario_generator import (
    GeneratedScenario,
)
from interventions.services.capacity import (
    HumanReviewCapacityAllocator,
    ReviewCandidate,
)
from interventions.services.decision import (
    AegisPayDecision,
    AegisPayDecisionService,
    DecisionStatus,
)
from interventions.services.selective_context_probe import (
    DecisionRelevantContextProbeService,
)
from risk.services.rules import RulesRiskEngine


@dataclass(frozen=True, slots=True)
class ScenarioOutcome:
    transaction_id: str
    scenario_type: str
    is_scam: bool

    base_risk_score: float
    final_risk_score: float

    context_requested: bool
    context_question_code: str | None

    requested_action: InterventionAction
    effective_action: InterventionAction

    review_requested: bool
    review_allocated: bool

    transaction_value: float
    protection_rate: float

    prevented_scam_value: float
    residual_scam_loss: float

    friction_cost: float
    operations_cost: float


@dataclass(frozen=True, slots=True)
class ExperimentSummary:
    total_scenarios: int

    scam_scenarios: int
    legitimate_scenarios: int

    context_probes: int

    requested_reviews: int
    allocated_reviews: int

    total_scam_value: float
    prevented_scam_value: float
    residual_scam_loss: float

    legitimate_friction_cost: float
    operations_cost: float


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    summary: ExperimentSummary
    outcomes: tuple[ScenarioOutcome, ...]


class AegisPayExperimentRunner:
    """
    Runs synthetic scenarios through the canonical AegisPay prototype
    Context Probe policy unless a decision service is explicitly supplied.

    Experimental ground truth is used only after the decision process
    when calculating evaluation metrics.

    It is never supplied to the risk engine, Context Probe, context-risk
    adjustment, or intervention policy.

    If the Context Probe requests information, the simulator supplies
    only the answer to that single selected question. Other hidden
    scenario context remains unavailable to the runtime decision.
    """

    def __init__(
        self,
        risk_engine=None,
        decision_service=None,
        capacity_allocator=None,
    ):
        self.risk_engine = (
            risk_engine
            or RulesRiskEngine()
        )

        self.decision_service = (
            decision_service
            or AegisPayDecisionService(
                context_probe=(
                    DecisionRelevantContextProbeService()
                )
            )
        )

        self.capacity_allocator = (
            capacity_allocator
            or HumanReviewCapacityAllocator()
        )

    def run(
        self,
        scenarios: list[GeneratedScenario],
        *,
        review_capacity: int,
    ) -> ExperimentResult:
        self._validate_scenarios(
            scenarios
        )

        completed_decisions = []

        context_metadata = {}

        for scenario in scenarios:
            transaction = scenario.transaction

            base_risk = self.risk_engine.assess(
                transaction
            )

            initial_decision = (
                self.decision_service.decide(
                    transaction=transaction,
                    base_risk=base_risk,
                )
            )

            context_requested = (
                initial_decision.status
                == DecisionStatus.NEEDS_CONTEXT
            )

            context_question_code = None

            if context_requested:
                question = (
                    initial_decision.context_question
                )

                context_question_code = (
                    question.code
                )

                simulated_answer = (
                    self._answer_selected_question(
                        scenario=scenario,
                        answer_key=question.answer_key,
                    )
                )

                final_decision = (
                    self.decision_service.decide(
                        transaction=transaction,
                        base_risk=base_risk,
                        context=simulated_answer,
                    )
                )

            else:
                final_decision = initial_decision

            if (
                final_decision.status
                != DecisionStatus.DECIDED
                or final_decision.policy is None
            ):
                raise RuntimeError(
                    "Experiment scenario did not reach "
                    "a completed intervention decision."
                )

            transaction_id = (
                transaction.transaction_id
            )

            completed_decisions.append(
                (
                    scenario,
                    final_decision,
                )
            )

            context_metadata[
                transaction_id
            ] = (
                context_requested,
                context_question_code,
            )

        review_candidates = [
            ReviewCandidate(
                transaction_id=(
                    scenario.transaction.transaction_id
                ),
                policy=decision.policy,
            )
            for (
                scenario,
                decision,
            ) in completed_decisions
        ]

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
            decision,
        ) in completed_decisions:
            transaction_id = (
                scenario.transaction.transaction_id
            )

            allocation = (
                allocation_by_id[
                    transaction_id
                ]
            )

            effective_evaluation = (
                self._evaluation_for_action(
                    decision=decision,
                    action=allocation.final_action,
                )
            )

            transaction_value = float(
                scenario.transaction.amount
            )

            if scenario.ground_truth.is_scam:
                prevented_scam_value = (
                    transaction_value
                    * effective_evaluation.protection_rate
                )

                residual_scam_loss = (
                    transaction_value
                    - prevented_scam_value
                )

            else:
                prevented_scam_value = 0.0
                residual_scam_loss = 0.0

            (
                context_requested,
                context_question_code,
            ) = context_metadata[
                transaction_id
            ]

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
                        decision.base_risk.score
                    ),
                    final_risk_score=(
                        decision.final_risk.score
                    ),
                    context_requested=(
                        context_requested
                    ),
                    context_question_code=(
                        context_question_code
                    ),
                    requested_action=(
                        decision.policy.action
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
                        effective_evaluation.protection_rate
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
                        effective_evaluation.friction_cost
                    ),
                    operations_cost=(
                        effective_evaluation.operations_cost
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
    def _answer_selected_question(
        *,
        scenario: GeneratedScenario,
        answer_key: str,
    ) -> ScamContext:
        scenario_value = getattr(
            scenario.context,
            answer_key,
        )

        answer_value = (
            scenario_value
            if scenario_value is not None
            else False
        )

        return ScamContext(
            **{
                answer_key: answer_value
            }
        )

    @staticmethod
    def _evaluation_for_action(
        *,
        decision: AegisPayDecision,
        action: InterventionAction,
    ):
        for evaluation in (
            decision.policy.evaluations
        ):
            if evaluation.action == action:
                return evaluation

        raise ValueError(
            f"No evaluation found for "
            f"{action.value}."
        )

    @staticmethod
    def _summarize(
        *,
        outcomes: list[ScenarioOutcome],
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
            context_probes=sum(
                1
                for outcome in outcomes
                if outcome.context_requested
            ),
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
                "Experiment transaction IDs "
                "must be unique."
            )