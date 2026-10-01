from dataclasses import dataclass

from experiments.services.friction import (
    CustomerFrictionAccounting,
)
from experiments.services.runner import (
    AegisPayExperimentRunner,
    ExperimentResult,
)
from experiments.services.scenario_generator import (
    GeneratedScenario,
)
from interventions.services.context_probe import (
    ContextProbeService,
)
from interventions.services.decision import (
    AegisPayDecisionService,
)
from interventions.services.selective_context_probe import (
    DecisionRelevantContextProbeService,
)


@dataclass(frozen=True, slots=True)
class ProbePolicyMetrics:
    strategy: str

    context_probes: int
    probe_rate: float

    prevention_rate: float
    prevented_scam_value: float
    residual_scam_loss: float

    legitimate_intervention_friction: float
    legitimate_probe_friction: float
    legitimate_total_friction: float

    requested_reviews: int
    allocated_reviews: int

    operations_cost: float
    total_modeled_cost: float


@dataclass(frozen=True, slots=True)
class ProbeSelectivityResult:
    review_capacity: int

    strategies: tuple[
        ProbePolicyMetrics,
        ...
    ]


class ProbeSelectivityComparisonService:
    LEGACY = "LEGACY_CONTEXT_PROBE"

    CANDIDATE = (
        "DECISION_RELEVANT_CONTEXT_PROBE"
    )

    def __init__(
        self,
        friction_accounting=None,
    ):
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
    ) -> ProbeSelectivityResult:
        if review_capacity < 0:
            raise ValueError(
                "Review capacity cannot be negative."
            )

        legacy_runner = (
            AegisPayExperimentRunner(
                decision_service=(
                    AegisPayDecisionService(
                        context_probe=(
                            ContextProbeService()
                        )
                    )
                )
            )
        )

        candidate_runner = (
            AegisPayExperimentRunner(
                decision_service=(
                    AegisPayDecisionService(
                        context_probe=(
                            DecisionRelevantContextProbeService()
                        )
                    )
                )
            )
        )

        legacy = legacy_runner.run(
            scenarios,
            review_capacity=review_capacity,
        )

        candidate = candidate_runner.run(
            scenarios,
            review_capacity=review_capacity,
        )

        return ProbeSelectivityResult(
            review_capacity=(
                review_capacity
            ),
            strategies=(
                self._metrics(
                    strategy=self.LEGACY,
                    result=legacy,
                ),
                self._metrics(
                    strategy=self.CANDIDATE,
                    result=candidate,
                ),
            ),
        )

    def _metrics(
        self,
        *,
        strategy: str,
        result: ExperimentResult,
    ) -> ProbePolicyMetrics:
        summary = result.summary

        friction = (
            self.friction_accounting.calculate(
                result
            )
        )

        if summary.total_scenarios > 0:
            probe_rate = (
                summary.context_probes
                / summary.total_scenarios
            )
        else:
            probe_rate = 0.0

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

        return ProbePolicyMetrics(
            strategy=strategy,
            context_probes=(
                summary.context_probes
            ),
            probe_rate=round(
                probe_rate,
                4,
            ),
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