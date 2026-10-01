import json
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from experiments.services.probe_friction_sensitivity import (
    FrictionSensitivityResult,
    ProbeFrictionSensitivityService,
)
from experiments.services.scenario_mixtures import (
    ScenarioMixtureBuilder,
)


class Command(BaseCommand):
    help = (
        "Evaluate Context Probe friction-cost sensitivity without "
        "rerunning runtime decisions."
    )

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=600)
        parser.add_argument("--seeds", default="7,21,42,84,126")
        parser.add_argument("--review-capacities", default="5,20")
        parser.add_argument(
            "--profiles",
            default=(
                "EQUAL_FAMILY,LEGITIMATE_DOMINANT,"
                "HARD_NEGATIVE_DOMINANT,SOCIAL_ENGINEERING_HEAVY,"
                "NETWORK_ABUSE_HEAVY"
            ),
        )
        parser.add_argument(
            "--probe-costs",
            default="0,10,25,50,100,200",
        )
        parser.add_argument("--output", default=None)

    def handle(self, *args, **options):
        try:
            seeds = self._parse_ints(options["seeds"], "seeds")
            capacities = self._parse_ints(
                options["review_capacities"],
                "review capacities",
            )
            profiles = self._parse_strings(
                options["profiles"],
                "profiles",
            )
            probe_costs = self._parse_costs(
                options["probe_costs"]
            )
            for profile in profiles:
                ScenarioMixtureBuilder.profile(profile)
            result = ProbeFrictionSensitivityService().run(
                count=options["count"],
                profiles=profiles,
                seeds=seeds,
                review_capacities=capacities,
                probe_costs=probe_costs,
            )
        except ValueError as error:
            raise CommandError(str(error)) from error

        payload = self._payload(result)
        self._print_result(payload)
        if options["output"]:
            path = Path(options["output"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Saved Context Probe friction sensitivity to {path}"
                )
            )

    @staticmethod
    def _parse_ints(value, label):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"--{label.replace(' ', '-')} must not be empty."
            )
        parts = value.split(",")
        if any(not part.strip() for part in parts):
            raise ValueError(
                f"--{label.replace(' ', '-')} contains an empty value."
            )
        try:
            return [int(part.strip()) for part in parts]
        except ValueError as error:
            raise ValueError(
                f"--{label.replace(' ', '-')} must be a comma-separated "
                "list of integers."
            ) from error

    @staticmethod
    def _parse_strings(value, label):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"--{label} must not be empty.")
        parts = [part.strip() for part in value.split(",")]
        if any(not part for part in parts):
            raise ValueError(f"--{label} contains an empty value.")
        return parts

    @staticmethod
    def _parse_costs(value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("--probe-costs must not be empty.")
        parts = value.split(",")
        if any(not part.strip() for part in parts):
            raise ValueError(
                "--probe-costs contains an empty value."
            )
        try:
            costs = [float(part.strip()) for part in parts]
        except ValueError as error:
            raise ValueError(
                "--probe-costs must be a comma-separated list of numbers."
            ) from error
        if any(cost < 0 for cost in costs):
            raise ValueError(
                "--probe-costs cannot contain negative values."
            )
        return costs

    @staticmethod
    def _payload(result: FrictionSensitivityResult):
        profiles = {}
        for name, profile in ScenarioMixtureBuilder.PROFILES.items():
            profiles[name] = {
                scenario_type.value: weight
                for scenario_type, weight in profile.weights.items()
            }

        def values(item, keys):
            return {
                key: getattr(item, key)
                for key in keys
            }

        run_keys = (
            "profile",
            "family_counts",
            "scenario_fingerprint",
            "seed",
            "review_capacity",
            "probe_cost",
            "strategy",
            "context_probes",
            "probe_rate",
            "prevention_rate",
            "prevented_scam_value",
            "residual_scam_loss",
            "legitimate_intervention_friction",
            "legitimate_probe_friction",
            "legitimate_total_friction",
            "requested_reviews",
            "allocated_reviews",
            "operations_cost",
            "total_modeled_cost",
        )
        return {
            "experiment": {
                "name": (
                    "AegisPay Context Probe Friction-Cost Sensitivity"
                ),
                "scenario_count": result.count,
                "profiles": list(result.profiles),
                "profile_definitions": profiles,
                "seeds": list(result.seeds),
                "review_capacities": list(result.review_capacities),
                "probe_costs": list(result.probe_costs),
                "current_default_probe_cost": (
                    ProbeFrictionSensitivityService.DEFAULT_PROBE_COST
                ),
                "base_runtime_cells": result.base_runtime_cells,
                "runtime_executions": result.runtime_executions,
                "evaluation_cells": result.evaluation_cells,
                "evaluation_rows": result.evaluation_rows,
                "candidate_status": "experimental_not_promoted",
                "ground_truth_usage": "evaluation_only",
                "delta_convention": "candidate_minus_legacy",
                "invariant": result.invariant,
                "invariant_violations": list(
                    result.invariant_violations
                ),
                "caveat": (
                    "Context Probe friction values are prototype "
                    "sensitivity assumptions, not measured upay "
                    "customer-friction or production economics."
                ),
            },
            "runs": [
                values(
                    run,
                    run_keys,
                )
                for run in result.runs
            ],
            "cells": [
                {
                    "profile": cell.profile,
                    "seed": cell.seed,
                    "review_capacity": cell.review_capacity,
                    "probe_cost": cell.probe_cost,
                    "family_counts": cell.family_counts,
                    "scenario_fingerprint": (
                        cell.scenario_fingerprint
                    ),
                    "deltas": cell.deltas,
                }
                for cell in result.cells
            ],
            "global_aggregates": [
                values(
                    aggregate,
                    (
                        "probe_cost",
                        "strategy",
                        "run_count",
                        "mean_legitimate_intervention_friction",
                        "mean_legitimate_probe_friction",
                        "mean_legitimate_total_friction",
                        "mean_total_modeled_cost",
                        "standard_deviation_total_modeled_cost",
                        "mean_prevention_rate",
                    ),
                )
                for aggregate in result.global_aggregates
            ],
            "cost_summaries": [
                values(
                    summary,
                    (
                        "probe_cost",
                        "cost_lower_cells",
                        "cost_equal_cells",
                        "cost_higher_cells",
                        "friction_lower_cells",
                        "friction_equal_cells",
                        "friction_higher_cells",
                        "probe_friction_lower_cells",
                        "probe_friction_equal_cells",
                        "probe_friction_higher_cells",
                        "minimum_total_cost_delta",
                        "maximum_total_cost_delta",
                        "mean_total_cost_delta",
                        "minimum_legitimate_friction_delta",
                        "maximum_legitimate_friction_delta",
                        "mean_legitimate_friction_delta",
                    ),
                )
                for summary in result.cost_summaries
            ],
            "profile_summaries": [
                values(
                    summary,
                    (
                        "profile",
                        "probe_cost",
                        "cost_lower_cells",
                        "cost_equal_cells",
                        "cost_higher_cells",
                        "friction_lower_cells",
                        "friction_equal_cells",
                        "friction_higher_cells",
                        "mean_total_cost_delta",
                        "mean_legitimate_friction_delta",
                    ),
                )
                for summary in result.profile_summaries
            ],
        }

    def _print_result(self, payload):
        experiment = payload["experiment"]
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "AegisPay Context Probe Friction-Cost Sensitivity"
            )
        )
        self.stdout.write(
            f"Profiles: {','.join(experiment['profiles'])}"
        )
        self.stdout.write(
            f"Seeds: {','.join(map(str, experiment['seeds']))} | "
            f"Capacities: "
            f"{','.join(map(str, experiment['review_capacities']))}"
        )
        self.stdout.write(
            f"Probe costs: "
            f"{','.join(map(str, experiment['probe_costs']))} | "
            f"Count: {experiment['scenario_count']}"
        )
        self.stdout.write(
            f"Base runtime cells: {experiment['base_runtime_cells']} | "
            f"Runtime executions: {experiment['runtime_executions']} | "
            f"Assumption-evaluation cells: "
            f"{experiment['evaluation_cells']}"
        )
        self.stdout.write("")

        header = (
            f"{'Cost':>8}"
            f"{'Strategy':<34}"
            f"{'Mean Probe Fric.':>19}"
            f"{'Mean Total Fric.':>19}"
            f"{'Mean Total Cost':>18}"
        )
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for item in payload["global_aggregates"]:
            self.stdout.write(
                f"{item['probe_cost']:>8.2f}"
                f"{item['strategy']:<34}"
                f"{item['mean_legitimate_probe_friction']:>19.2f}"
                f"{item['mean_legitimate_total_friction']:>19.2f}"
                f"{item['mean_total_modeled_cost']:>18.2f}"
            )

        self.stdout.write("")
        self.stdout.write("Candidate summary by probe cost")
        for item in payload["cost_summaries"]:
            self.stdout.write(
                f"{item['probe_cost']:.2f}: "
                f"cost lower/equal/higher "
                f"{item['cost_lower_cells']}/"
                f"{item['cost_equal_cells']}/"
                f"{item['cost_higher_cells']}; "
                f"friction lower/equal/higher "
                f"{item['friction_lower_cells']}/"
                f"{item['friction_equal_cells']}/"
                f"{item['friction_higher_cells']}; "
                f"mean delta {item['mean_total_cost_delta']:.2f}; "
                f"worst {item['maximum_total_cost_delta']:.2f}; "
                f"best {item['minimum_total_cost_delta']:.2f}"
            )

        regressions = [
            item["probe_cost"]
            for item in payload["cost_summaries"]
            if item["cost_higher_cells"] > 0
        ]
        self.stdout.write("")
        self.stdout.write(
            "Any candidate total-cost regression in tested grid: "
            f"{'YES' if regressions else 'NO'}"
        )
        if regressions:
            self.stdout.write(
                "Affected probe costs: "
                + ", ".join(map(str, regressions))
            )
        self.stdout.write(
            "Context Probe friction values are prototype sensitivity "
            "assumptions, not measured upay customer-friction or "
            "production economics."
        )
