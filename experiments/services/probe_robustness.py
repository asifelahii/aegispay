from dataclasses import dataclass
from hashlib import sha256
import json
from statistics import mean, pstdev

from experiments.services.probe_selectivity import (
    ProbePolicyMetrics,
    ProbeSelectivityComparisonService,
)
from experiments.services.scenario_generator import (
    GeneratedScenario,
    SyntheticScenarioGenerator,
)


@dataclass(frozen=True, slots=True)
class RobustnessRunMetrics:
    seed: int
    review_capacity: int
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
class CapacityAggregate:
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
class RobustnessCell:
    seed: int
    review_capacity: int
    scenario_fingerprint: str
    strategies: tuple[RobustnessRunMetrics, ...]


@dataclass(frozen=True, slots=True)
class RobustnessSummary:
    total_cells: int
    candidate_fewer_probe_cells: int
    candidate_prevention_better_cells: int
    candidate_prevention_equal_cells: int
    candidate_prevention_worse_cells: int
    candidate_total_cost_better_cells: int
    candidate_total_cost_equal_cells: int
    candidate_total_cost_worse_cells: int
    candidate_legitimate_friction_better_cells: int
    worst_prevention_delta: float
    best_prevention_delta: float
    worst_total_cost_delta: float
    best_total_cost_delta: float


@dataclass(frozen=True, slots=True)
class ProbeRobustnessResult:
    count: int
    seeds: tuple[int, ...]
    review_capacities: tuple[int, ...]
    cells: tuple[RobustnessCell, ...]
    runs: tuple[RobustnessRunMetrics, ...]
    aggregates: tuple[CapacityAggregate, ...]
    summary: RobustnessSummary


class ProbeRobustnessService:
    """Runs the fixed-seed, fixed-capacity Context Probe comparison grid."""

    LEGACY = ProbeSelectivityComparisonService.LEGACY
    CANDIDATE = ProbeSelectivityComparisonService.CANDIDATE

    def __init__(
        self,
        comparison_service=None,
        scenario_generator_factory=None,
    ):
        self.comparison_service = (
            comparison_service
            or ProbeSelectivityComparisonService()
        )
        self.scenario_generator_factory = (
            scenario_generator_factory
            or SyntheticScenarioGenerator
        )

    def run(
        self,
        *,
        count: int,
        seeds: list[int] | tuple[int, ...],
        review_capacities: list[int] | tuple[int, ...],
    ) -> ProbeRobustnessResult:
        self._validate_inputs(
            count=count,
            seeds=seeds,
            review_capacities=review_capacities,
        )

        normalized_seeds = tuple(seeds)
        normalized_capacities = tuple(
            review_capacities
        )
        cells = []

        for seed in normalized_seeds:
            scenarios = self.scenario_generator_factory(
                seed=seed
            ).generate(
                count=count,
                start_time=self._start_time(),
            )
            fingerprint = self._scenario_fingerprint(
                scenarios
            )

            for review_capacity in normalized_capacities:
                comparison = (
                    self.comparison_service.compare(
                        scenarios,
                        review_capacity=review_capacity,
                    )
                )
                metrics = tuple(
                    self._run_metrics(
                        seed=seed,
                        review_capacity=review_capacity,
                        item=item,
                    )
                    for item in comparison.strategies
                )
                self._validate_review_capacity(
                    metrics,
                    review_capacity,
                )
                cells.append(
                    RobustnessCell(
                        seed=seed,
                        review_capacity=review_capacity,
                        scenario_fingerprint=fingerprint,
                        strategies=metrics,
                    )
                )

        runs = tuple(
            metric
            for cell in cells
            for metric in cell.strategies
        )

        return ProbeRobustnessResult(
            count=count,
            seeds=normalized_seeds,
            review_capacities=normalized_capacities,
            cells=tuple(cells),
            runs=runs,
            aggregates=self._aggregates(
                runs
            ),
            summary=self._summary(cells),
        )

    @staticmethod
    def _start_time():
        from datetime import UTC, datetime

        return datetime(
            2026,
            10,
            1,
            tzinfo=UTC,
        )

    @staticmethod
    def _validate_inputs(
        *,
        count: int,
        seeds,
        review_capacities,
    ) -> None:
        if count <= 0:
            raise ValueError(
                "Scenario count must be greater than zero."
            )

        if not seeds:
            raise ValueError(
                "At least one seed is required."
            )

        if not review_capacities:
            raise ValueError(
                "At least one review capacity is required."
            )

        if any(
            not isinstance(seed, int)
            for seed in seeds
        ):
            raise ValueError(
                "Seeds must be integers."
            )

        if any(
            not isinstance(capacity, int)
            for capacity in review_capacities
        ):
            raise ValueError(
                "Review capacities must be integers."
            )

        if any(
            capacity < 0
            for capacity in review_capacities
        ):
            raise ValueError(
                "Review capacities cannot be negative."
            )

    @staticmethod
    def _validate_review_capacity(
        metrics: tuple[RobustnessRunMetrics, ...],
        review_capacity: int,
    ) -> None:
        if any(
            item.allocated_reviews > review_capacity
            for item in metrics
        ):
            raise RuntimeError(
                "Allocated reviews exceeded review capacity."
            )

    @staticmethod
    def _scenario_fingerprint(
        scenarios: list[GeneratedScenario],
    ) -> str:
        values = [
            {
                "transaction_id": scenario.transaction.transaction_id,
                "amount": str(scenario.transaction.amount),
                "scenario_type": scenario.scenario_type.value,
            }
            for scenario in scenarios
        ]
        encoded = json.dumps(
            values,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    @staticmethod
    def _run_metrics(
        *,
        seed: int,
        review_capacity: int,
        item: ProbePolicyMetrics,
    ) -> RobustnessRunMetrics:
        return RobustnessRunMetrics(
            seed=seed,
            review_capacity=review_capacity,
            strategy=item.strategy,
            context_probes=item.context_probes,
            probe_rate=item.probe_rate,
            prevention_rate=item.prevention_rate,
            prevented_scam_value=item.prevented_scam_value,
            residual_scam_loss=item.residual_scam_loss,
            legitimate_intervention_friction=(
                item.legitimate_intervention_friction
            ),
            legitimate_probe_friction=(
                item.legitimate_probe_friction
            ),
            legitimate_total_friction=(
                item.legitimate_total_friction
            ),
            requested_reviews=item.requested_reviews,
            allocated_reviews=item.allocated_reviews,
            operations_cost=item.operations_cost,
            total_modeled_cost=item.total_modeled_cost,
        )

    def _aggregates(
        self,
        runs: tuple[RobustnessRunMetrics, ...],
    ) -> tuple[CapacityAggregate, ...]:
        aggregates = []
        capacities = sorted({
            run.review_capacity
            for run in runs
        })

        for capacity in capacities:
            for strategy in (
                self.LEGACY,
                self.CANDIDATE,
            ):
                items = [
                    run
                    for run in runs
                    if (
                        run.review_capacity == capacity
                        and run.strategy == strategy
                    )
                ]
                aggregates.append(
                    CapacityAggregate(
                        review_capacity=capacity,
                        strategy=strategy,
                        seed_count=len(items),
                        mean_probe_rate=self._mean(
                            item.probe_rate
                            for item in items
                        ),
                        standard_deviation_probe_rate=(
                            self._standard_deviation(
                                item.probe_rate
                                for item in items
                            )
                        ),
                        mean_prevention_rate=self._mean(
                            item.prevention_rate
                            for item in items
                        ),
                        standard_deviation_prevention_rate=(
                            self._standard_deviation(
                                item.prevention_rate
                                for item in items
                            )
                        ),
                        mean_residual_scam_loss=self._mean(
                            item.residual_scam_loss
                            for item in items
                        ),
                        mean_legitimate_total_friction=(
                            self._mean(
                                item.legitimate_total_friction
                                for item in items
                            )
                        ),
                        mean_allocated_reviews=self._mean(
                            item.allocated_reviews
                            for item in items
                        ),
                        mean_total_modeled_cost=self._mean(
                            item.total_modeled_cost
                            for item in items
                        ),
                        standard_deviation_total_modeled_cost=(
                            self._standard_deviation(
                                item.total_modeled_cost
                                for item in items
                            )
                        ),
                    )
                )

        return tuple(aggregates)

    @staticmethod
    def _mean(values) -> float:
        return round(mean(values), 4)

    @staticmethod
    def _standard_deviation(values) -> float:
        values = list(values)
        return round(
            pstdev(values) if len(values) > 1 else 0.0,
            4,
        )

    def _summary(
        self,
        cells: list[RobustnessCell],
    ) -> RobustnessSummary:
        deltas = [
            self._deltas(cell)
            for cell in cells
        ]

        return RobustnessSummary(
            total_cells=len(cells),
            candidate_fewer_probe_cells=sum(
                delta["probe"] < 0
                for delta in deltas
            ),
            candidate_prevention_better_cells=sum(
                delta["prevention"] > 0
                for delta in deltas
            ),
            candidate_prevention_equal_cells=sum(
                delta["prevention"] == 0
                for delta in deltas
            ),
            candidate_prevention_worse_cells=sum(
                delta["prevention"] < 0
                for delta in deltas
            ),
            candidate_total_cost_better_cells=sum(
                delta["total_cost"] < 0
                for delta in deltas
            ),
            candidate_total_cost_equal_cells=sum(
                delta["total_cost"] == 0
                for delta in deltas
            ),
            candidate_total_cost_worse_cells=sum(
                delta["total_cost"] > 0
                for delta in deltas
            ),
            candidate_legitimate_friction_better_cells=sum(
                delta["friction"] < 0
                for delta in deltas
            ),
            worst_prevention_delta=round(
                min(delta["prevention"] for delta in deltas),
                4,
            ),
            best_prevention_delta=round(
                max(delta["prevention"] for delta in deltas),
                4,
            ),
            worst_total_cost_delta=round(
                max(delta["total_cost"] for delta in deltas),
                2,
            ),
            best_total_cost_delta=round(
                min(delta["total_cost"] for delta in deltas),
                2,
            ),
        )

    def _deltas(
        self,
        cell: RobustnessCell,
    ) -> dict[str, float]:
        by_strategy = {
            item.strategy: item
            for item in cell.strategies
        }
        legacy = by_strategy[self.LEGACY]
        candidate = by_strategy[self.CANDIDATE]
        return {
            "probe": (
                candidate.context_probes
                - legacy.context_probes
            ),
            "prevention": (
                candidate.prevention_rate
                - legacy.prevention_rate
            ),
            "total_cost": (
                candidate.total_modeled_cost
                - legacy.total_modeled_cost
            ),
            "friction": (
                candidate.legitimate_total_friction
                - legacy.legitimate_total_friction
            ),
        }
