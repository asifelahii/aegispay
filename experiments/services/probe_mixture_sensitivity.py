from dataclasses import dataclass
from statistics import mean, pstdev

from experiments.services.probe_selectivity import (
    ProbePolicyMetrics,
    ProbeSelectivityComparisonService,
)
from experiments.services.scenario_mixtures import (
    ScenarioMixtureBuilder,
)


@dataclass(frozen=True, slots=True)
class MixtureRunMetrics:
    profile: str
    family_counts: dict[str, int]
    seed: int
    review_capacity: int
    strategy: str
    scenario_fingerprint: str
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
class MixtureCell:
    profile: str
    seed: int
    review_capacity: int
    scenario_fingerprint: str
    family_counts: dict[str, int]
    strategies: tuple[MixtureRunMetrics, ...]
    deltas: dict[str, float]


@dataclass(frozen=True, slots=True)
class MixtureAggregate:
    profile: str
    review_capacity: int
    strategy: str
    seed_count: int
    mean_probe_rate: float
    standard_deviation_probe_rate: float
    mean_prevention_rate: float
    standard_deviation_prevention_rate: float
    mean_residual_scam_loss: float
    mean_legitimate_total_friction: float
    mean_allocated_reviews: float
    mean_total_modeled_cost: float
    standard_deviation_total_modeled_cost: float


@dataclass(frozen=True, slots=True)
class MixtureProfileSummary:
    profile: str
    total_cells: int
    candidate_fewer_probe_cells: int
    prevention_better_cells: int
    prevention_equal_cells: int
    prevention_worse_cells: int
    friction_lower_cells: int
    friction_equal_cells: int
    friction_higher_cells: int
    cost_lower_cells: int
    cost_equal_cells: int
    cost_higher_cells: int
    minimum_prevention_delta: float
    maximum_prevention_delta: float
    minimum_total_cost_delta: float
    maximum_total_cost_delta: float
    mean_review_allocation_delta: float


@dataclass(frozen=True, slots=True)
class MixtureGlobalSummary:
    total_cells: int
    candidate_fewer_probe_cells: int
    prevention_better_cells: int
    prevention_equal_cells: int
    prevention_worse_cells: int
    friction_lower_cells: int
    friction_equal_cells: int
    friction_higher_cells: int
    cost_lower_cells: int
    cost_equal_cells: int
    cost_higher_cells: int
    worst_prevention_delta: float
    best_prevention_delta: float
    worst_total_cost_delta: float
    best_total_cost_delta: float
    largest_positive_review_allocation_delta: float


@dataclass(frozen=True, slots=True)
class MixtureSensitivityResult:
    count: int
    profiles: tuple[str, ...]
    seeds: tuple[int, ...]
    review_capacities: tuple[int, ...]
    cells: tuple[MixtureCell, ...]
    runs: tuple[MixtureRunMetrics, ...]
    aggregates: tuple[MixtureAggregate, ...]
    profile_summaries: tuple[MixtureProfileSummary, ...]
    global_summary: MixtureGlobalSummary


class ProbeMixtureSensitivityService:
    LEGACY = ProbeSelectivityComparisonService.LEGACY
    CANDIDATE = ProbeSelectivityComparisonService.CANDIDATE

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
    ) -> MixtureSensitivityResult:
        self._validate_inputs(
            count=count,
            profiles=profiles,
            seeds=seeds,
            review_capacities=review_capacities,
        )
        cells = []
        for profile in profiles:
            for seed in seeds:
                population = self.mixture_builder.build(
                    profile=profile,
                    count=count,
                    seed=seed,
                )
                for capacity in review_capacities:
                    comparison = self.comparison_service.compare(
                        list(population.scenarios),
                        review_capacity=capacity,
                    )
                    metrics = tuple(
                        self._run_metrics(
                            profile=profile,
                            population=population,
                            seed=seed,
                            review_capacity=capacity,
                            item=item,
                        )
                        for item in comparison.strategies
                    )
                    if any(
                        item.allocated_reviews > capacity
                        for item in metrics
                    ):
                        raise RuntimeError(
                            "Allocated reviews exceeded capacity."
                        )
                    cells.append(
                        MixtureCell(
                            profile=profile,
                            seed=seed,
                            review_capacity=capacity,
                            scenario_fingerprint=population.fingerprint,
                            family_counts=population.family_counts,
                            strategies=metrics,
                            deltas=self._deltas(metrics),
                        )
                    )

        runs = tuple(
            run
            for cell in cells
            for run in cell.strategies
        )
        return MixtureSensitivityResult(
            count=count,
            profiles=tuple(profiles),
            seeds=tuple(seeds),
            review_capacities=tuple(review_capacities),
            cells=tuple(cells),
            runs=runs,
            aggregates=self._aggregates(runs),
            profile_summaries=self._profile_summaries(cells),
            global_summary=self._global_summary(cells),
        )

    @staticmethod
    def _validate_inputs(
        *,
        count,
        profiles,
        seeds,
        review_capacities,
    ):
        if count <= 0:
            raise ValueError(
                "Scenario count must be greater than zero."
            )
        if not profiles:
            raise ValueError(
                "At least one profile is required."
            )
        if not seeds:
            raise ValueError(
                "At least one seed is required."
            )
        if not review_capacities:
            raise ValueError(
                "At least one review capacity is required."
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

    @staticmethod
    def _run_metrics(
        *,
        profile,
        population,
        seed,
        review_capacity,
        item: ProbePolicyMetrics,
    ):
        return MixtureRunMetrics(
            profile=profile,
            family_counts=population.family_counts,
            seed=seed,
            review_capacity=review_capacity,
            strategy=item.strategy,
            scenario_fingerprint=population.fingerprint,
            context_probes=item.context_probes,
            probe_rate=item.probe_rate,
            prevention_rate=item.prevention_rate,
            prevented_scam_value=item.prevented_scam_value,
            residual_scam_loss=item.residual_scam_loss,
            legitimate_intervention_friction=(
                item.legitimate_intervention_friction
            ),
            legitimate_probe_friction=item.legitimate_probe_friction,
            legitimate_total_friction=item.legitimate_total_friction,
            requested_reviews=item.requested_reviews,
            allocated_reviews=item.allocated_reviews,
            operations_cost=item.operations_cost,
            total_modeled_cost=item.total_modeled_cost,
        )

    @staticmethod
    def _deltas(metrics):
        by_strategy = {
            item.strategy: item
            for item in metrics
        }
        legacy = by_strategy[
            ProbeMixtureSensitivityService.LEGACY
        ]
        candidate = by_strategy[
            ProbeMixtureSensitivityService.CANDIDATE
        ]
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

    def _aggregates(self, runs):
        aggregates = []
        for profile in sorted({run.profile for run in runs}):
            for capacity in sorted({
                run.review_capacity
                for run in runs
                if run.profile == profile
            }):
                for strategy in (self.LEGACY, self.CANDIDATE):
                    items = [
                        run
                        for run in runs
                        if (
                            run.profile == profile
                            and run.review_capacity == capacity
                            and run.strategy == strategy
                        )
                    ]
                    aggregates.append(
                        MixtureAggregate(
                            profile=profile,
                            review_capacity=capacity,
                            strategy=strategy,
                            seed_count=len(items),
                            mean_probe_rate=self._mean(
                                item.probe_rate for item in items
                            ),
                            standard_deviation_probe_rate=(
                                self._sd(
                                    item.probe_rate for item in items
                                )
                            ),
                            mean_prevention_rate=self._mean(
                                item.prevention_rate for item in items
                            ),
                            standard_deviation_prevention_rate=(
                                self._sd(
                                    item.prevention_rate for item in items
                                )
                            ),
                            mean_residual_scam_loss=self._mean(
                                item.residual_scam_loss for item in items
                            ),
                            mean_legitimate_total_friction=self._mean(
                                item.legitimate_total_friction
                                for item in items
                            ),
                            mean_allocated_reviews=self._mean(
                                item.allocated_reviews for item in items
                            ),
                            mean_total_modeled_cost=self._mean(
                                item.total_modeled_cost for item in items
                            ),
                            standard_deviation_total_modeled_cost=(
                                self._sd(
                                    item.total_modeled_cost
                                    for item in items
                                )
                            ),
                        )
                    )
        return tuple(aggregates)

    def _profile_summaries(self, cells):
        summaries = []
        for profile in sorted({cell.profile for cell in cells}):
            deltas = [
                cell.deltas
                for cell in cells
                if cell.profile == profile
            ]
            summaries.append(
                MixtureProfileSummary(
                    profile=profile,
                    total_cells=len(deltas),
                    candidate_fewer_probe_cells=sum(
                        delta["probe_rate"] < 0
                        for delta in deltas
                    ),
                    prevention_better_cells=sum(
                        delta["prevention_rate"] > 0
                        for delta in deltas
                    ),
                    prevention_equal_cells=sum(
                        delta["prevention_rate"] == 0
                        for delta in deltas
                    ),
                    prevention_worse_cells=sum(
                        delta["prevention_rate"] < 0
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
                    minimum_prevention_delta=min(
                        delta["prevention_rate"]
                        for delta in deltas
                    ),
                    maximum_prevention_delta=max(
                        delta["prevention_rate"]
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
                    mean_review_allocation_delta=self._mean(
                        delta["allocated_reviews"]
                        for delta in deltas
                    ),
                )
            )
        return tuple(summaries)

    def _global_summary(self, cells):
        deltas = [cell.deltas for cell in cells]
        return MixtureGlobalSummary(
            total_cells=len(deltas),
            candidate_fewer_probe_cells=sum(
                delta["probe_rate"] < 0 for delta in deltas
            ),
            prevention_better_cells=sum(
                delta["prevention_rate"] > 0 for delta in deltas
            ),
            prevention_equal_cells=sum(
                delta["prevention_rate"] == 0 for delta in deltas
            ),
            prevention_worse_cells=sum(
                delta["prevention_rate"] < 0 for delta in deltas
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
            cost_lower_cells=sum(
                delta["total_modeled_cost"] < 0 for delta in deltas
            ),
            cost_equal_cells=sum(
                delta["total_modeled_cost"] == 0 for delta in deltas
            ),
            cost_higher_cells=sum(
                delta["total_modeled_cost"] > 0 for delta in deltas
            ),
            worst_prevention_delta=min(
                delta["prevention_rate"] for delta in deltas
            ),
            best_prevention_delta=max(
                delta["prevention_rate"] for delta in deltas
            ),
            worst_total_cost_delta=max(
                delta["total_modeled_cost"] for delta in deltas
            ),
            best_total_cost_delta=min(
                delta["total_modeled_cost"] for delta in deltas
            ),
            largest_positive_review_allocation_delta=max(
                delta["allocated_reviews"] for delta in deltas
            ),
        )

    @staticmethod
    def _mean(values):
        return round(mean(list(values)), 4)

    @staticmethod
    def _sd(values):
        values = list(values)
        return round(pstdev(values) if len(values) > 1 else 0.0, 4)
