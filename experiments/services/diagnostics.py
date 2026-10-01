from collections import Counter, defaultdict
from dataclasses import dataclass

from experiments.services.baselines import (
    BaselineExperimentRunner,
    BaselineStrategy,
)
from experiments.services.runner import (
    AegisPayExperimentRunner,
    ExperimentResult,
)
from experiments.services.scenario_generator import (
    GeneratedScenario,
    ScenarioType,
)


@dataclass(frozen=True, slots=True)
class ActionCount:
    action: str
    count: int


@dataclass(frozen=True, slots=True)
class QuestionCount:
    question_code: str
    count: int


@dataclass(frozen=True, slots=True)
class ScenarioStrategyDiagnostics:
    strategy: str
    scenario_type: str

    total_scenarios: int
    scam_scenarios: int
    legitimate_scenarios: int

    average_base_risk: float
    average_final_risk: float

    context_probes: int

    requested_reviews: int
    allocated_reviews: int

    prevented_scam_value: float
    residual_scam_loss: float
    scam_prevention_rate: float

    legitimate_friction_cost: float
    operations_cost: float

    action_counts: tuple[
        ActionCount,
        ...
    ]

    question_counts: tuple[
        QuestionCount,
        ...
    ]


@dataclass(frozen=True, slots=True)
class ExperimentDiagnosticsResult:
    review_capacity: int
    rows: tuple[
        ScenarioStrategyDiagnostics,
        ...
    ]


class ExperimentDiagnosticsService:
    """
    Produces scenario-level diagnostics for all baseline strategies
    and full AegisPay.

    The purpose is diagnostic rather than optimization.

    This service does not alter thresholds, risk weights, intervention
    assumptions, or scenario definitions. It only aggregates outcomes
    produced by the existing experiment runners.
    """

    AEGISPAY = "AEGISPAY"

    def __init__(
        self,
        baseline_runner=None,
        aegispay_runner=None,
    ):
        self.baseline_runner = (
            baseline_runner
            or BaselineExperimentRunner()
        )

        self.aegispay_runner = (
            aegispay_runner
            or AegisPayExperimentRunner()
        )

    def analyze(
        self,
        scenarios: list[
            GeneratedScenario
        ],
        *,
        review_capacity: int,
    ) -> ExperimentDiagnosticsResult:
        if review_capacity < 0:
            raise ValueError(
                "Review capacity cannot be negative."
            )

        strategy_results = []

        for strategy in (
            BaselineStrategy.NO_INTERVENTION,
            BaselineStrategy.HARD_THRESHOLD,
            BaselineStrategy.STATIC_TIER,
        ):
            result = (
                self.baseline_runner.run(
                    scenarios,
                    strategy=strategy,
                    review_capacity=review_capacity,
                )
            )

            strategy_results.append(
                (
                    strategy.value,
                    result,
                )
            )

        aegispay_result = (
            self.aegispay_runner.run(
                scenarios,
                review_capacity=review_capacity,
            )
        )

        strategy_results.append(
            (
                self.AEGISPAY,
                aegispay_result,
            )
        )

        rows = []

        for (
            strategy,
            result,
        ) in strategy_results:
            rows.extend(
                self._breakdown(
                    strategy=strategy,
                    result=result,
                )
            )

        return ExperimentDiagnosticsResult(
            review_capacity=review_capacity,
            rows=tuple(rows),
        )

    @staticmethod
    def _breakdown(
        *,
        strategy: str,
        result: ExperimentResult,
    ) -> list[
        ScenarioStrategyDiagnostics
    ]:
        grouped = defaultdict(list)

        for outcome in result.outcomes:
            grouped[
                outcome.scenario_type
            ].append(outcome)

        scenario_order = {
            scenario_type.value: index
            for (
                index,
                scenario_type,
            ) in enumerate(
                ScenarioType
            )
        }

        ordered_types = sorted(
            grouped,
            key=lambda scenario_type: (
                scenario_order.get(
                    scenario_type,
                    999,
                )
            ),
        )

        rows = []

        for scenario_type in ordered_types:
            outcomes = grouped[
                scenario_type
            ]

            total = len(
                outcomes
            )

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

            action_counter = Counter(
                outcome.effective_action.value
                for outcome in outcomes
            )

            question_counter = Counter(
                outcome.context_question_code
                for outcome in outcomes
                if (
                    outcome.context_question_code
                    is not None
                )
            )

            prevented_scam_value = sum(
                outcome.prevented_scam_value
                for outcome
                in scam_outcomes
            )

            residual_scam_loss = sum(
                outcome.residual_scam_loss
                for outcome
                in scam_outcomes
            )

            total_scam_value = (
                prevented_scam_value
                + residual_scam_loss
            )

            if total_scam_value > 0:
                scam_prevention_rate = (
                    prevented_scam_value
                    / total_scam_value
                )
            else:
                scam_prevention_rate = 0.0

            rows.append(
                ScenarioStrategyDiagnostics(
                    strategy=strategy,
                    scenario_type=(
                        scenario_type
                    ),
                    total_scenarios=total,
                    scam_scenarios=len(
                        scam_outcomes
                    ),
                    legitimate_scenarios=len(
                        legitimate_outcomes
                    ),
                    average_base_risk=round(
                        sum(
                            outcome.base_risk_score
                            for outcome
                            in outcomes
                        )
                        / total,
                        4,
                    ),
                    average_final_risk=round(
                        sum(
                            outcome.final_risk_score
                            for outcome
                            in outcomes
                        )
                        / total,
                        4,
                    ),
                    context_probes=sum(
                        1
                        for outcome
                        in outcomes
                        if outcome.context_requested
                    ),
                    requested_reviews=sum(
                        1
                        for outcome
                        in outcomes
                        if outcome.review_requested
                    ),
                    allocated_reviews=sum(
                        1
                        for outcome
                        in outcomes
                        if outcome.review_allocated
                    ),
                    prevented_scam_value=round(
                        prevented_scam_value,
                        2,
                    ),
                    residual_scam_loss=round(
                        residual_scam_loss,
                        2,
                    ),
                    scam_prevention_rate=round(
                        scam_prevention_rate,
                        4,
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
                    action_counts=tuple(
                        ActionCount(
                            action=action,
                            count=count,
                        )
                        for (
                            action,
                            count,
                        ) in sorted(
                            action_counter.items()
                        )
                    ),
                    question_counts=tuple(
                        QuestionCount(
                            question_code=question_code,
                            count=count,
                        )
                        for (
                            question_code,
                            count,
                        ) in sorted(
                            question_counter.items()
                        )
                    ),
                )
            )

        return rows