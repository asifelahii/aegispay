from collections import Counter
from dataclasses import dataclass
from statistics import mean, pstdev

from core.contracts import InterventionAction
from experiments.services.friction import CustomerFrictionAccounting
from experiments.services.intervention_assumptions import (
    ExperimentInterventionPolicy,
    InterventionAssumptionBuilder,
)
from experiments.services.runner import AegisPayExperimentRunner
from experiments.services.scenario_mixtures import ScenarioMixtureBuilder
from interventions.services.context_probe import ContextProbeService
from interventions.services.decision import AegisPayDecisionService
from interventions.services.selective_context_probe import (
    DecisionRelevantContextProbeService,
)


@dataclass(frozen=True, slots=True)
class InterventionSensitivityRun:
    profile: str
    family_counts: dict[str, int]
    scenario_fingerprint: str
    seed: int
    review_capacity: int
    assumption: str
    strategy: str
    metrics: dict
    requested_action_counts: dict[str, int]
    effective_action_counts: dict[str, int]
    requested_actions: tuple[str, ...]
    effective_actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InterventionSensitivityCell:
    profile: str
    seed: int
    review_capacity: int
    assumption: str
    family_counts: dict[str, int]
    scenario_fingerprint: str
    strategies: tuple[InterventionSensitivityRun, ...]
    deltas: dict[str, float]


@dataclass(frozen=True, slots=True)
class InterventionSensitivityResult:
    count: int
    profiles: tuple[str, ...]
    seeds: tuple[int, ...]
    review_capacities: tuple[int, ...]
    assumptions: tuple[str, ...]
    assumption_definitions: dict
    cells: tuple[InterventionSensitivityCell, ...]
    runs: tuple[InterventionSensitivityRun, ...]
    global_aggregates: tuple[dict, ...]
    candidate_summaries: tuple[dict, ...]
    global_candidate_summary: dict
    review_capacity_summary: tuple[dict, ...]
    decision_change_analysis: tuple[dict, ...]
    regressions: tuple[dict, ...]


class ProbeInterventionSensitivityService:
    LEGACY = "LEGACY_CONTEXT_PROBE"
    CANDIDATE = "DECISION_RELEVANT_CONTEXT_PROBE"
    ACTIONS = tuple(action.value for action in InterventionAction)

    def run(self, *, count, profiles, seeds, review_capacities, assumptions):
        self._validate_inputs(
            count, profiles, seeds, review_capacities, assumptions
        )
        definitions = {
            name: InterventionAssumptionBuilder.build(name)
            for name in assumptions
        }
        cells = []
        regressions = []
        for profile in profiles:
            for seed in seeds:
                population = ScenarioMixtureBuilder().build(
                    profile=profile, count=count, seed=seed
                )
                for capacity in review_capacities:
                    for assumption in assumptions:
                        policy = ExperimentInterventionPolicy(
                            definitions[assumption].profiles
                        )
                        legacy, candidate = self._run_pair(
                            population.scenarios, capacity, policy
                        )
                        metrics = tuple(
                            self._run_metrics(
                                population, profile, seed, capacity,
                                assumption, strategy, result,
                            )
                            for strategy, result in (
                                (self.LEGACY, legacy),
                                (self.CANDIDATE, candidate),
                            )
                        )
                        if any(
                            item.metrics["allocated_reviews"] > capacity
                            for item in metrics
                        ):
                            raise RuntimeError(
                                "Allocated reviews exceeded capacity."
                            )
                        cell = InterventionSensitivityCell(
                            profile=profile,
                            seed=seed,
                            review_capacity=capacity,
                            assumption=assumption,
                            family_counts=population.family_counts,
                            scenario_fingerprint=population.fingerprint,
                            strategies=metrics,
                            deltas=self._deltas(metrics),
                        )
                        cells.append(cell)
                        regressions.extend(
                            self._regressions(cell)
                        )
        runs = tuple(run for cell in cells for run in cell.strategies)
        return InterventionSensitivityResult(
            count=count,
            profiles=tuple(profiles),
            seeds=tuple(seeds),
            review_capacities=tuple(review_capacities),
            assumptions=tuple(assumptions),
            assumption_definitions={
                name: definitions[name].as_dict() for name in assumptions
            },
            cells=tuple(cells),
            runs=runs,
            global_aggregates=self._global_aggregates(cells),
            candidate_summaries=self._candidate_summaries(cells),
            global_candidate_summary=self._candidate_summary(
                cells,
                scope="all_assumptions",
            ),
            review_capacity_summary=self._review_summary(cells),
            decision_change_analysis=self._decision_changes(cells),
            regressions=tuple(regressions),
        )

    @staticmethod
    def _run_pair(scenarios, capacity, policy):
        def runner(probe):
            return AegisPayExperimentRunner(
                decision_service=AegisPayDecisionService(
                    context_probe=probe,
                    intervention_policy=policy,
                )
            ).run(list(scenarios), review_capacity=capacity)

        return runner(ContextProbeService()), runner(
            DecisionRelevantContextProbeService(
                intervention_policy=policy
            )
        )

    def _run_metrics(
        self, population, profile, seed, capacity, assumption, strategy, result
    ):
        summary = result.summary
        friction = CustomerFrictionAccounting().calculate(result)
        total = (
            summary.residual_scam_loss
            + friction.legitimate_total_customer_friction_cost
            + summary.operations_cost
        )
        requested = Counter(
            outcome.requested_action.value for outcome in result.outcomes
        )
        effective = Counter(
            outcome.effective_action.value for outcome in result.outcomes
        )
        metrics = {
            "context_probes": summary.context_probes,
            "probe_rate": round(summary.context_probes / summary.total_scenarios, 4),
            "prevention_rate": round(
                summary.prevented_scam_value / summary.total_scam_value, 4
            ) if summary.total_scam_value else 0.0,
            "prevented_scam_value": summary.prevented_scam_value,
            "residual_scam_loss": summary.residual_scam_loss,
            "legitimate_intervention_friction": (
                friction.legitimate_intervention_friction_cost
            ),
            "legitimate_probe_friction": (
                friction.legitimate_context_probe_friction_cost
            ),
            "legitimate_total_friction": (
                friction.legitimate_total_customer_friction_cost
            ),
            "requested_reviews": summary.requested_reviews,
            "allocated_reviews": summary.allocated_reviews,
            "operations_cost": summary.operations_cost,
            "total_modeled_cost": round(total, 2),
        }
        return InterventionSensitivityRun(
            profile=profile,
            family_counts=population.family_counts,
            scenario_fingerprint=population.fingerprint,
            seed=seed,
            review_capacity=capacity,
            assumption=assumption,
            strategy=strategy,
            metrics=metrics,
            requested_action_counts={
                action: requested.get(action, 0) for action in self.ACTIONS
            },
            effective_action_counts={
                action: effective.get(action, 0) for action in self.ACTIONS
            },
            requested_actions=tuple(
                outcome.requested_action.value for outcome in result.outcomes
            ),
            effective_actions=tuple(
                outcome.effective_action.value for outcome in result.outcomes
            ),
        )

    @staticmethod
    def _deltas(metrics):
        legacy, candidate = metrics
        keys = (
            "probe_rate", "prevention_rate", "residual_scam_loss",
            "legitimate_total_friction", "requested_reviews",
            "allocated_reviews", "operations_cost", "total_modeled_cost",
        )
        return {
            key: round(
                candidate.metrics[key] - legacy.metrics[key], 4
            ) for key in keys
        }

    def _candidate_summaries(self, cells):
        result = []
        for assumption in sorted({cell.assumption for cell in cells}):
            selected = [cell for cell in cells if cell.assumption == assumption]
            result.append(
                self._candidate_summary(
                    selected,
                    scope=assumption,
                )
            )
        return tuple(result)

    @staticmethod
    def _candidate_summary(cells, *, scope):
        deltas = [cell.deltas for cell in cells]
        return {
            "scope": scope,
            "assumption": scope if scope != "all_assumptions" else None,
            "total_cells": len(cells),
            "candidate_fewer_probe_cells": sum(
                item["probe_rate"] < 0 for item in deltas
            ),
            "prevention_better_cells": sum(
                item["prevention_rate"] > 0 for item in deltas
            ),
            "prevention_equal_cells": sum(
                item["prevention_rate"] == 0 for item in deltas
            ),
            "prevention_worse_cells": sum(
                item["prevention_rate"] < 0 for item in deltas
            ),
            "friction_lower_cells": sum(
                item["legitimate_total_friction"] < 0 for item in deltas
            ),
            "friction_equal_cells": sum(
                item["legitimate_total_friction"] == 0 for item in deltas
            ),
            "friction_higher_cells": sum(
                item["legitimate_total_friction"] > 0 for item in deltas
            ),
            "cost_lower_cells": sum(
                item["total_modeled_cost"] < 0 for item in deltas
            ),
            "cost_equal_cells": sum(
                item["total_modeled_cost"] == 0 for item in deltas
            ),
            "cost_higher_cells": sum(
                item["total_modeled_cost"] > 0 for item in deltas
            ),
            "minimum_prevention_delta": min(
                item["prevention_rate"] for item in deltas
            ),
            "maximum_prevention_delta": max(
                item["prevention_rate"] for item in deltas
            ),
            "mean_prevention_delta": mean(
                item["prevention_rate"] for item in deltas
            ),
            "minimum_total_cost_delta": min(
                item["total_modeled_cost"] for item in deltas
            ),
            "maximum_total_cost_delta": max(
                item["total_modeled_cost"] for item in deltas
            ),
            "mean_total_cost_delta": mean(
                item["total_modeled_cost"] for item in deltas
            ),
            "mean_allocated_review_delta": mean(
                item["allocated_reviews"] for item in deltas
            ),
            "largest_allocated_review_delta": max(
                item["allocated_reviews"] for item in deltas
            ),
        }

    def _global_aggregates(self, cells):
        result = []
        for assumption in sorted({cell.assumption for cell in cells}):
            for strategy in (self.LEGACY, self.CANDIDATE):
                runs = [
                    run for cell in cells if cell.assumption == assumption
                    for run in cell.strategies if run.strategy == strategy
                ]
                def avg(key):
                    return round(mean(run.metrics[key] for run in runs), 4)
                result.append({
                    "assumption": assumption,
                    "strategy": strategy,
                    "run_count": len(runs),
                    "mean_probe_rate": avg("probe_rate"),
                    "mean_prevention_rate": avg("prevention_rate"),
                    "mean_residual_scam_loss": avg("residual_scam_loss"),
                    "mean_legitimate_total_friction": avg(
                        "legitimate_total_friction"
                    ),
                    "mean_requested_reviews": avg("requested_reviews"),
                    "mean_allocated_reviews": avg("allocated_reviews"),
                    "mean_operations_cost": avg("operations_cost"),
                    "mean_total_modeled_cost": avg("total_modeled_cost"),
                    "standard_deviation_total_modeled_cost": round(
                        pstdev(run.metrics["total_modeled_cost"] for run in runs), 4
                    ),
                })
        return tuple(result)

    @staticmethod
    def _review_summary(cells):
        result = []
        for assumption in sorted({cell.assumption for cell in cells}):
            entries = {"assumption": assumption}
            for strategy in (
                ProbeInterventionSensitivityService.LEGACY,
                ProbeInterventionSensitivityService.CANDIDATE,
            ):
                runs = [
                    run for cell in cells if cell.assumption == assumption
                    for run in cell.strategies if run.strategy == strategy
                ]
                entries[strategy] = {
                    "mean_requested_reviews": mean(
                        run.metrics["requested_reviews"] for run in runs
                    ),
                    "mean_allocated_reviews": mean(
                        run.metrics["allocated_reviews"] for run in runs
                    ),
                    "full_capacity_cells": sum(
                        run.metrics["allocated_reviews"] == run.review_capacity
                        for run in runs
                    ),
                    "maximum_requested_reviews": max(
                        run.metrics["requested_reviews"] for run in runs
                    ),
                    "maximum_allocated_reviews": max(
                        run.metrics["allocated_reviews"] for run in runs
                    ),
                }
            result.append(entries)
        return tuple(result)

    def _decision_changes(self, cells):
        baseline = {
            (cell.profile, cell.seed, cell.review_capacity):
            cell for cell in cells if cell.assumption == "BASELINE"
        }
        result = []
        for assumption in sorted({cell.assumption for cell in cells} - {"BASELINE"}):
            for strategy in (self.LEGACY, self.CANDIDATE):
                comparisons = []
                for cell in cells:
                    if cell.assumption != assumption:
                        continue
                    current = next(
                        run for run in cell.strategies if run.strategy == strategy
                    )
                    base = baseline[
                        (cell.profile, cell.seed, cell.review_capacity)
                    ]
                    before = next(
                        run for run in base.strategies if run.strategy == strategy
                    )
                    total = sum(before.requested_action_counts.values())
                    comparisons.append({
                        "requested": sum(
                            previous != updated
                            for previous, updated in zip(
                                before.requested_actions,
                                current.requested_actions,
                            )
                        ),
                        "effective": sum(
                            previous != updated
                            for previous, updated in zip(
                                before.effective_actions,
                                current.effective_actions,
                            )
                        ),
                        "total": total,
                    })
                result.append({
                    "assumption": assumption,
                    "strategy": strategy,
                    "mean_requested_action_change_rate": mean(
                        item["requested"] / item["total"]
                        for item in comparisons
                    ),
                    "mean_effective_action_change_rate": mean(
                        item["effective"] / item["total"]
                        for item in comparisons
                    ),
                })
        return tuple(result)

    @staticmethod
    def _regressions(cell):
        legacy, candidate = cell.strategies
        values = (
            ("prevention_rate", "candidate prevention regression"),
            ("legitimate_total_friction", "candidate legitimate friction regression"),
            ("total_modeled_cost", "candidate modeled cost regression"),
        )
        result = []
        for key, description in values:
            delta = candidate.metrics[key] - legacy.metrics[key]
            if delta < 0 if key == "prevention_rate" else delta > 0:
                result.append({
                    "profile": cell.profile,
                    "seed": cell.seed,
                    "review_capacity": cell.review_capacity,
                    "assumption": cell.assumption,
                    "metric": key,
                    "description": description,
                    "candidate_value": candidate.metrics[key],
                    "legacy_value": legacy.metrics[key],
                    "delta": round(delta, 4),
                })
        return result

    @staticmethod
    def _validate_inputs(count, profiles, seeds, capacities, assumptions):
        if count <= 0:
            raise ValueError("Scenario count must be greater than zero.")
        if not profiles:
            raise ValueError("At least one profile is required.")
        if not seeds:
            raise ValueError("At least one seed is required.")
        if not capacities:
            raise ValueError("At least one review capacity is required.")
        if not assumptions:
            raise ValueError("At least one assumption profile is required.")
        if any(not isinstance(seed, int) for seed in seeds):
            raise ValueError("Seeds must be integers.")
        if any(not isinstance(capacity, int) or capacity < 0 for capacity in capacities):
            raise ValueError("Review capacities must be non-negative integers.")
        for profile in profiles:
            ScenarioMixtureBuilder.profile(profile)
        for assumption in assumptions:
            InterventionAssumptionBuilder.build(assumption)
