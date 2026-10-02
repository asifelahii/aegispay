from dataclasses import dataclass

from experiments.services.baselines import (
    BaselineExperimentRunner,
    BaselineStrategy,
)
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
from interventions.services.decision import (
    AegisPayDecisionService,
)
from interventions.services.selective_context_probe import (
    DecisionRelevantContextProbeService,
)


@dataclass(frozen=True, slots=True)
class StrategyMetrics:
    strategy: str

    total_scenarios: int
    scam_scenarios: int
    legitimate_scenarios: int

    context_probes: int

    requested_reviews: int
    allocated_reviews: int

    total_scam_value: float
    prevented_scam_value: float
    residual_scam_loss: float

    prevention_rate: float

    legitimate_friction_cost: float
    legitimate_context_probe_friction_cost: float
    legitimate_total_customer_friction_cost: float

    operations_cost: float

    total_modeled_cost: float

    protected_value_per_review: float
    friction_per_legitimate_transaction: float


@dataclass(frozen=True, slots=True)
class PolicyComparisonResult:
    review_capacity: int
    strategies: tuple[
        StrategyMetrics,
        ...
    ]


class PolicyComparisonService:
    """
    Evaluates conventional intervention baselines and full AegisPay
    against the same scenarios and review-capacity constraint.

    Comparison metrics are derived only after each strategy has
    completed its runtime decisions.

    Ground-truth labels therefore remain evaluation metadata rather
    than runtime decision inputs.

    Customer friction is decomposed into:
    1. intervention friction
    2. Context Probe friction
    3. total customer friction
    """

    AEGISPAY = "AEGISPAY"

    def __init__(
        self,
        baseline_runner=None,
        aegispay_runner=None,
        friction_accounting=None,
    ):
        self.baseline_runner = (
            baseline_runner
            or BaselineExperimentRunner()
        )

        self.aegispay_runner = (
            aegispay_runner
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
    ) -> PolicyComparisonResult:
        if review_capacity < 0:
            raise ValueError(
                "Review capacity cannot be negative."
            )

        results = []

        for strategy in (
            BaselineStrategy.NO_INTERVENTION,
            BaselineStrategy.HARD_THRESHOLD,
            BaselineStrategy.STATIC_TIER,
        ):
            result = self.baseline_runner.run(
                scenarios,
                strategy=strategy,
                review_capacity=review_capacity,
            )

            results.append(
                self._metrics(
                    strategy=strategy.value,
                    result=result,
                )
            )

        aegispay_result = (
            self.aegispay_runner.run(
                scenarios,
                review_capacity=review_capacity,
            )
        )

        results.append(
            self._metrics(
                strategy=self.AEGISPAY,
                result=aegispay_result,
            )
        )

        return PolicyComparisonResult(
            review_capacity=review_capacity,
            strategies=tuple(results),
        )

    def _metrics(
        self,
        *,
        strategy: str,
        result: ExperimentResult,
    ) -> StrategyMetrics:
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

        if summary.allocated_reviews > 0:
            protected_value_per_review = (
                summary.prevented_scam_value
                / summary.allocated_reviews
            )
        else:
            protected_value_per_review = 0.0

        if summary.legitimate_scenarios > 0:
            friction_per_legitimate = (
                friction.legitimate_total_customer_friction_cost
                / summary.legitimate_scenarios
            )
        else:
            friction_per_legitimate = 0.0

        total_modeled_cost = (
            summary.residual_scam_loss
            + friction.legitimate_total_customer_friction_cost
            + summary.operations_cost
        )

        return StrategyMetrics(
            strategy=strategy,
            total_scenarios=(
                summary.total_scenarios
            ),
            scam_scenarios=(
                summary.scam_scenarios
            ),
            legitimate_scenarios=(
                summary.legitimate_scenarios
            ),
            context_probes=(
                summary.context_probes
            ),
            requested_reviews=(
                summary.requested_reviews
            ),
            allocated_reviews=(
                summary.allocated_reviews
            ),
            total_scam_value=(
                summary.total_scam_value
            ),
            prevented_scam_value=(
                summary.prevented_scam_value
            ),
            residual_scam_loss=(
                summary.residual_scam_loss
            ),
            prevention_rate=round(
                prevention_rate,
                4,
            ),
            legitimate_friction_cost=(
                friction.legitimate_intervention_friction_cost
            ),
            legitimate_context_probe_friction_cost=(
                friction.legitimate_context_probe_friction_cost
            ),
            legitimate_total_customer_friction_cost=(
                friction.legitimate_total_customer_friction_cost
            ),
            operations_cost=(
                summary.operations_cost
            ),
            total_modeled_cost=round(
                total_modeled_cost,
                2,
            ),
            protected_value_per_review=round(
                protected_value_per_review,
                2,
            ),
            friction_per_legitimate_transaction=round(
                friction_per_legitimate,
                2,
            ),
        )