from dataclasses import dataclass
from statistics import mean, pstdev

from experiments.services.friction import (
    CustomerFrictionAccounting,
    FrictionAssumptions,
)
from experiments.services.probe_selectivity import (
    ProbeSelectivityComparisonService,
)
from experiments.services.scenario_mixtures import (
    ScenarioMixtureBuilder,
)
from experiments.services.runner import (
    ExperimentResult,
)


@dataclass(frozen=True, slots=True)
class FrictionSensitivityRun:
    profile: str
    family_counts: dict[str, int]
    scenario_fingerprint: str
    seed: int
    review_capacity: int
    probe_cost: float
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
class FrictionSensitivityCell:
    profile: str
    seed: int
    review_capacity: int
    probe_cost: float
    family_counts: dict[str, int]
    scenario_fingerprint: str
    strategies: tuple[FrictionSensitivityRun, ...]
    deltas: dict[str, float]


@dataclass(frozen=True, slots=True)
class FrictionGlobalAggregate:
    probe_cost: float
    strategy: str
    run_count: int
    mean_legitimate_intervention_friction: float
    mean_legitimate_probe_friction: float
    mean_legitimate_total_friction: float
    mean_total_modeled_cost: float
    standard_deviation_total_modeled_cost: float
    mean_prevention_rate: float


@dataclass(frozen=True, slots=True)
class FrictionCostSummary:
    probe_cost: float
    cost_lower_cells: int
    cost_equal_cells: int
    cost_higher_cells: int
    friction_lower_cells: int
    friction_equal_cells: int
    friction_higher_cells: int
    probe_friction_lower_cells: int
    probe_friction_equal_cells: int
    probe_friction_higher_cells: int
    minimum_total_cost_delta: float
    maximum_total_cost_delta: float
    mean_total_cost_delta: float
    minimum_legitimate_friction_delta: float
    maximum_legitimate_friction_delta: float
    mean_legitimate_friction_delta: float


@dataclass(frozen=True, slots=True)
class FrictionProfileSummary:
    profile: str
    probe_cost: float
    cost_lower_cells: int
    cost_equal_cells: int
    cost_higher_cells: int
    friction_lower_cells: int
    friction_equal_cells: int
    friction_higher_cells: int
    mean_total_cost_delta: float
    mean_legitimate_friction_delta: float


@dataclass(frozen=True, slots=True)
class FrictionSensitivityResult:
    count: int
    profiles: tuple[str, ...]
    seeds: tuple[int, ...]
    review_capacities: tuple[int, ...]
    probe_costs: tuple[float, ...]
    base_runtime_cells: int
    runtime_executions: int
    evaluation_cells: int
    evaluation_rows: int
    cells: tuple[FrictionSensitivityCell, ...]
    runs: tuple[FrictionSensitivityRun, ...]
    global_aggregates: tuple[FrictionGlobalAggregate, ...]
    cost_summaries: tuple[FrictionCostSummary, ...]
    profile_summaries: tuple[FrictionProfileSummary, ...]
    invariant: bool
    invariant_violations: tuple[str, ...]


class ProbeFrictionSensitivityService:
    """Re-accounts fixed runtime outcomes under probe-cost assumptions."""

    LEGACY = ProbeSelectivityComparisonService.LEGACY
    CANDIDATE = ProbeSelectivityComparisonService.CANDIDATE
    DEFAULT_PROBE_COST = 25.0

    def __init__(
        self,
        comparison_service=None,
        mixture_builder=None,
    ):
        self.comparison_service = (
            comparison_service
            or ProbeSelectivityComparisonService()
        )
        self.mixture_builder = (
            mixture_builder
            or ScenarioMixtureBuilder()
        )

    def run(
        self,
        *,
        count: int,
        profiles,
        seeds,
        review_capacities,
        probe_costs,
    ) -> FrictionSensitivityResult:
        self._validate_inputs(
            count=count,
            profiles=profiles,
            seeds=seeds,
            review_capacities=review_capacities,
            probe_costs=probe_costs,
        )
        base_results = []
        for profile in profiles:
            for seed in seeds:
                population = self.mixture_builder.build(
                    profile=profile,
                    count=count,
                    seed=seed,
                )
                for capacity in review_capacities:
                    outcomes = self.comparison_service.run_results(
                        list(population.scenarios),
                        review_capacity=capacity,
                    )
                    base_results.append(
                        (
                            profile,
                            seed,
                            capacity,
                            population,
                            outcomes,
                        )
                    )

        cells = []
        for (
            profile,
            seed,
            capacity,
            population,
            outcomes,
        ) in base_results:
            for probe_cost in probe_costs:
                metrics = tuple(
                    self._metrics(
                        profile=profile,
                        seed=seed,
                        capacity=capacity,
                        probe_cost=probe_cost,
                        population=population,
                        result=result,
                        strategy=strategy,
                    )
                    for strategy, result in (
                        (self.LEGACY, outcomes[0]),
                        (self.CANDIDATE, outcomes[1]),
                    )
                )
                cells.append(
                    FrictionSensitivityCell(
                        profile=profile,
                        seed=seed,
                        review_capacity=capacity,
                        probe_cost=probe_cost,
                        family_counts=population.family_counts,
                        scenario_fingerprint=population.fingerprint,
                        strategies=metrics,
                        deltas=self._deltas(metrics),
                    )
                )

        runs = tuple(
            run
            for cell in cells
            for run in cell.strategies
        )
        invariant_violations = self._invariant_violations(
            cells
        )
        return FrictionSensitivityResult(
            count=count,
            profiles=tuple(profiles),
            seeds=tuple(seeds),
            review_capacities=tuple(review_capacities),
            probe_costs=tuple(probe_costs),
            base_runtime_cells=len(base_results),
            runtime_executions=len(base_results) * 2,
            evaluation_cells=len(cells),
            evaluation_rows=len(runs),
            cells=tuple(cells),
            runs=runs,
            global_aggregates=self._global_aggregates(runs),
            cost_summaries=self._cost_summaries(cells),
            profile_summaries=self._profile_summaries(cells),
            invariant=not invariant_violations,
            invariant_violations=tuple(
                invariant_violations
            ),
        )

    @staticmethod
    def _validate_inputs(
        *,
        count,
        profiles,
        seeds,
        review_capacities,
        probe_costs,
    ):
        if count <= 0:
            raise ValueError(
                "Scenario count must be greater than zero."
            )
        if not profiles or not seeds or not review_capacities:
            raise ValueError(
                "Profiles, seeds, and review capacities are required."
            )
        if not probe_costs:
            raise ValueError(
                "At least one probe cost is required."
            )
        if any(not isinstance(seed, int) for seed in seeds):
            raise ValueError("Seeds must be integers.")
        if any(
            not isinstance(capacity, int)
            for capacity in review_capacities
        ):
            raise ValueError(
                "Review capacities must be integers."
            )
        if any(capacity < 0 for capacity in review_capacities):
            raise ValueError(
                "Review capacities cannot be negative."
            )
        if any(
            not isinstance(cost, (int, float))
            or cost < 0
            for cost in probe_costs
        ):
            raise ValueError(
                "Probe costs must be non-negative numbers."
            )

    @staticmethod
    def _metrics(
        *,
        profile,
        seed,
        capacity,
        probe_cost,
        population,
        result: ExperimentResult,
        strategy,
    ):
        summary = result.summary
        friction = CustomerFrictionAccounting(
            assumptions=FrictionAssumptions(
                context_probe_cost=probe_cost,
            )
        ).calculate(result)
        prevention_rate = (
            summary.prevented_scam_value
            / summary.total_scam_value
            if summary.total_scam_value
            else 0.0
        )
        total_cost = (
            summary.residual_scam_loss
            + friction.legitimate_total_customer_friction_cost
            + summary.operations_cost
        )
        return FrictionSensitivityRun(
            profile=profile,
            family_counts=population.family_counts,
            scenario_fingerprint=population.fingerprint,
            seed=seed,
            review_capacity=capacity,
            probe_cost=float(probe_cost),
            strategy=strategy,
            context_probes=summary.context_probes,
            probe_rate=round(
                summary.context_probes
                / summary.total_scenarios,
                4,
            ),
            prevention_rate=round(prevention_rate, 4),
            prevented_scam_value=summary.prevented_scam_value,
            residual_scam_loss=summary.residual_scam_loss,
            legitimate_intervention_friction=(
                friction.legitimate_intervention_friction_cost
            ),
            legitimate_probe_friction=(
                friction.legitimate_context_probe_friction_cost
            ),
            legitimate_total_friction=(
                friction.legitimate_total_customer_friction_cost
            ),
            requested_reviews=summary.requested_reviews,
            allocated_reviews=summary.allocated_reviews,
            operations_cost=summary.operations_cost,
            total_modeled_cost=round(total_cost, 2),
        )

    @classmethod
    def _deltas(cls, metrics):
        by_strategy = {
            metric.strategy: metric
            for metric in metrics
        }
        legacy = by_strategy[cls.LEGACY]
        candidate = by_strategy[cls.CANDIDATE]
        return {
            "probe_rate": round(
                candidate.probe_rate - legacy.probe_rate,
                4,
            ),
            "prevention_rate": round(
                candidate.prevention_rate
                - legacy.prevention_rate,
                4,
            ),
            "residual_scam_loss": round(
                candidate.residual_scam_loss
                - legacy.residual_scam_loss,
                2,
            ),
            "legitimate_intervention_friction": round(
                candidate.legitimate_intervention_friction
                - legacy.legitimate_intervention_friction,
                2,
            ),
            "legitimate_probe_friction": round(
                candidate.legitimate_probe_friction
                - legacy.legitimate_probe_friction,
                2,
            ),
            "legitimate_total_friction": round(
                candidate.legitimate_total_friction
                - legacy.legitimate_total_friction,
                2,
            ),
            "allocated_reviews": (
                candidate.allocated_reviews
                - legacy.allocated_reviews
            ),
            "total_modeled_cost": round(
                candidate.total_modeled_cost
                - legacy.total_modeled_cost,
                2,
            ),
        }

    @staticmethod
    def _mean(values):
        return round(mean(list(values)), 4)

    @staticmethod
    def _sd(values):
        values = list(values)
        return round(pstdev(values) if len(values) > 1 else 0.0, 4)

    def _global_aggregates(self, runs):
        result = []
        for cost in sorted({run.probe_cost for run in runs}):
            for strategy in (self.LEGACY, self.CANDIDATE):
                items = [
                    run
                    for run in runs
                    if (
                        run.probe_cost == cost
                        and run.strategy == strategy
                    )
                ]
                result.append(
                    FrictionGlobalAggregate(
                        probe_cost=cost,
                        strategy=strategy,
                        run_count=len(items),
                        mean_legitimate_intervention_friction=(
                            self._mean(
                                item.legitimate_intervention_friction
                                for item in items
                            )
                        ),
                        mean_legitimate_probe_friction=self._mean(
                            item.legitimate_probe_friction
                            for item in items
                        ),
                        mean_legitimate_total_friction=self._mean(
                            item.legitimate_total_friction
                            for item in items
                        ),
                        mean_total_modeled_cost=self._mean(
                            item.total_modeled_cost
                            for item in items
                        ),
                        standard_deviation_total_modeled_cost=(
                            self._sd(
                                item.total_modeled_cost
                                for item in items
                            )
                        ),
                        mean_prevention_rate=self._mean(
                            item.prevention_rate
                            for item in items
                        ),
                    )
                )
        return tuple(result)

    def _cost_summaries(self, cells):
        result = []
        for cost in sorted({cell.probe_cost for cell in cells}):
            deltas = [
                cell.deltas
                for cell in cells
                if cell.probe_cost == cost
            ]
            result.append(
                FrictionCostSummary(
                    probe_cost=cost,
                    cost_lower_cells=sum(
                        delta["total_modeled_cost"] < 0
                        for delta in deltas
                    ),
                    cost_equal_cells=sum(
                        delta["total_modeled_cost"] == 0
                        for delta in deltas
                    ),
                    cost_higher_cells=sum(
                        delta["total_modeled_cost"] > 0
                        for delta in deltas
                    ),
                    friction_lower_cells=sum(
                        delta["legitimate_total_friction"] < 0
                        for delta in deltas
                    ),
                    friction_equal_cells=sum(
                        delta["legitimate_total_friction"] == 0
                        for delta in deltas
                    ),
                    friction_higher_cells=sum(
                        delta["legitimate_total_friction"] > 0
                        for delta in deltas
                    ),
                    probe_friction_lower_cells=sum(
                        delta["legitimate_probe_friction"] < 0
                        for delta in deltas
                    ),
                    probe_friction_equal_cells=sum(
                        delta["legitimate_probe_friction"] == 0
                        for delta in deltas
                    ),
                    probe_friction_higher_cells=sum(
                        delta["legitimate_probe_friction"] > 0
                        for delta in deltas
                    ),
                    minimum_total_cost_delta=min(
                        delta["total_modeled_cost"]
                        for delta in deltas
                    ),
                    maximum_total_cost_delta=max(
                        delta["total_modeled_cost"]
                        for delta in deltas
                    ),
                    mean_total_cost_delta=self._mean(
                        delta["total_modeled_cost"]
                        for delta in deltas
                    ),
                    minimum_legitimate_friction_delta=min(
                        delta["legitimate_total_friction"]
                        for delta in deltas
                    ),
                    maximum_legitimate_friction_delta=max(
                        delta["legitimate_total_friction"]
                        for delta in deltas
                    ),
                    mean_legitimate_friction_delta=self._mean(
                        delta["legitimate_total_friction"]
                        for delta in deltas
                    ),
                )
            )
        return tuple(result)

    def _profile_summaries(self, cells):
        result = []
        for profile in sorted({cell.profile for cell in cells}):
            for cost in sorted({
                cell.probe_cost
                for cell in cells
                if cell.profile == profile
            }):
                deltas = [
                    cell.deltas
                    for cell in cells
                    if (
                        cell.profile == profile
                        and cell.probe_cost == cost
                    )
                ]
                result.append(
                    FrictionProfileSummary(
                        profile=profile,
                        probe_cost=cost,
                        cost_lower_cells=sum(
                            delta["total_modeled_cost"] < 0
                            for delta in deltas
                        ),
                        cost_equal_cells=sum(
                            delta["total_modeled_cost"] == 0
                            for delta in deltas
                        ),
                        cost_higher_cells=sum(
                            delta["total_modeled_cost"] > 0
                            for delta in deltas
                        ),
                        friction_lower_cells=sum(
                            delta["legitimate_total_friction"] < 0
                            for delta in deltas
                        ),
                        friction_equal_cells=sum(
                            delta["legitimate_total_friction"] == 0
                            for delta in deltas
                        ),
                        friction_higher_cells=sum(
                            delta["legitimate_total_friction"] > 0
                            for delta in deltas
                        ),
                        mean_total_cost_delta=self._mean(
                            delta["total_modeled_cost"]
                            for delta in deltas
                        ),
                        mean_legitimate_friction_delta=self._mean(
                            delta["legitimate_total_friction"]
                            for delta in deltas
                        ),
                    )
                )
        return tuple(result)

    def _invariant_violations(self, cells):
        grouped = {}
        for cell in cells:
            for run in cell.strategies:
                key = (
                    cell.profile,
                    cell.seed,
                    cell.review_capacity,
                    run.strategy,
                )
                grouped.setdefault(key, []).append(run)

        violations = []
        fields = (
            "context_probes",
            "probe_rate",
            "prevention_rate",
            "prevented_scam_value",
            "residual_scam_loss",
            "requested_reviews",
            "allocated_reviews",
            "operations_cost",
            "legitimate_intervention_friction",
        )
        for key, runs in grouped.items():
            for field in fields:
                if len({
                    getattr(run, field)
                    for run in runs
                }) > 1:
                    violations.append(
                        f"{key}:{field}"
                    )
        return violations
