import json
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from experiments.services.probe_mixture_sensitivity import (
    MixtureSensitivityResult,
    ProbeMixtureSensitivityService,
)
from experiments.services.scenario_mixtures import (
    ScenarioMixtureBuilder,
)


class Command(BaseCommand):
    help = (
        "Run Context Probe sensitivity across synthetic "
        "scenario-mixture profiles."
    )

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=600)
        parser.add_argument(
            "--seeds",
            default="7,21,42,84,126",
        )
        parser.add_argument(
            "--review-capacities",
            default="5,20",
        )
        parser.add_argument(
            "--profiles",
            default="EQUAL_FAMILY,LEGITIMATE_DOMINANT,"
            "HARD_NEGATIVE_DOMINANT,SOCIAL_ENGINEERING_HEAVY,"
            "NETWORK_ABUSE_HEAVY",
        )
        parser.add_argument("--output", default=None)

    def handle(self, *args, **options):
        try:
            seeds = self._parse_integer_list(
                options["seeds"],
                "seeds",
            )
            capacities = self._parse_integer_list(
                options["review_capacities"],
                "review capacities",
            )
            profiles = self._parse_string_list(
                options["profiles"],
                "profiles",
            )
            for profile in profiles:
                ScenarioMixtureBuilder.profile(profile)
            result = ProbeMixtureSensitivityService().run(
                count=options["count"],
                profiles=profiles,
                seeds=seeds,
                review_capacities=capacities,
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
                    f"Saved Context Probe mixture sensitivity to {path}"
                )
            )

    @staticmethod
    def _parse_integer_list(value, label):
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
    def _parse_string_list(value, label):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"--{label} must not be empty."
            )
        parts = [part.strip() for part in value.split(",")]
        if any(not part for part in parts):
            raise ValueError(
                f"--{label} contains an empty value."
            )
        return parts

    @staticmethod
    def _payload(result: MixtureSensitivityResult):
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
            "seed",
            "review_capacity",
            "strategy",
            "scenario_fingerprint",
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
        aggregate_keys = (
            "profile",
            "review_capacity",
            "strategy",
            "seed_count",
            "mean_probe_rate",
            "standard_deviation_probe_rate",
            "mean_prevention_rate",
            "standard_deviation_prevention_rate",
            "mean_residual_scam_loss",
            "mean_legitimate_total_friction",
            "mean_allocated_reviews",
            "mean_total_modeled_cost",
            "standard_deviation_total_modeled_cost",
        )

        return {
            "experiment": {
                "name": (
                    "AegisPay Context Probe Scenario-Mixture "
                    "Sensitivity"
                ),
                "scenario_count": result.count,
                "profiles": list(result.profiles),
                "profile_definitions": profiles,
                "seeds": list(result.seeds),
                "review_capacities": list(
                    result.review_capacities
                ),
                "controlled_cells": len(result.cells),
                "strategy_runs": len(result.runs),
                "scenario_source": "synthetic_prototype",
                "ground_truth_usage": "evaluation_only",
                "candidate_status": "experimental_not_promoted",
                "standard_deviation": "population",
                "delta_convention": "candidate_minus_legacy",
                "caveat": (
                    "These are synthetic scenario-mixture stress tests. "
                    "The configured profile weights are experimental "
                    "benchmark assumptions and are not estimates of real "
                    "upay fraud prevalence or production transaction "
                    "distributions."
                ),
            },
            "runs": [
                values(run, run_keys)
                for run in result.runs
            ],
            "cells": [
                {
                    "profile": cell.profile,
                    "seed": cell.seed,
                    "review_capacity": cell.review_capacity,
                    "scenario_fingerprint": (
                        cell.scenario_fingerprint
                    ),
                    "family_counts": cell.family_counts,
                    "deltas": cell.deltas,
                }
                for cell in result.cells
            ],
            "aggregates": [
                values(aggregate, aggregate_keys)
                for aggregate in result.aggregates
            ],
            "profile_summaries": [
                values(
                    summary,
                    (
                        "profile",
                        "total_cells",
                        "candidate_fewer_probe_cells",
                        "prevention_better_cells",
                        "prevention_equal_cells",
                        "prevention_worse_cells",
                        "friction_lower_cells",
                        "friction_equal_cells",
                        "friction_higher_cells",
                        "cost_lower_cells",
                        "cost_equal_cells",
                        "cost_higher_cells",
                        "minimum_prevention_delta",
                        "maximum_prevention_delta",
                        "minimum_total_cost_delta",
                        "maximum_total_cost_delta",
                        "mean_review_allocation_delta",
                    ),
                )
                for summary in result.profile_summaries
            ],
            "global_summary": values(
                result.global_summary,
                (
                    "total_cells",
                    "candidate_fewer_probe_cells",
                    "prevention_better_cells",
                    "prevention_equal_cells",
                    "prevention_worse_cells",
                    "friction_lower_cells",
                    "friction_equal_cells",
                    "friction_higher_cells",
                    "cost_lower_cells",
                    "cost_equal_cells",
                    "cost_higher_cells",
                    "worst_prevention_delta",
                    "best_prevention_delta",
                    "worst_total_cost_delta",
                    "best_total_cost_delta",
                    "largest_positive_review_allocation_delta",
                ),
            ),
        }

    def _print_result(self, payload):
        experiment = payload["experiment"]
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "AegisPay Context Probe Scenario-Mixture Sensitivity"
            )
        )
        self.stdout.write(
            f"Count: {experiment['scenario_count']} | "
            f"Seeds: {','.join(map(str, experiment['seeds']))} | "
            f"Capacities: "
            f"{','.join(map(str, experiment['review_capacities']))}"
        )
        self.stdout.write(
            f"Profiles: {','.join(experiment['profiles'])} | "
            f"Controlled cells: {experiment['controlled_cells']}"
        )
        self.stdout.write("")

        header = (
            f"{'Profile':<28}"
            f"{'Cap':>5}"
            f"{'Strategy':<34}"
            f"{'Probe %':>10}"
            f"{'Prevent %':>12}"
            f"{'Legit Fric.':>15}"
            f"{'Reviews':>10}"
            f"{'Total Cost':>16}"
        )
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for item in payload["aggregates"]:
            self.stdout.write(
                f"{item['profile']:<28}"
                f"{item['review_capacity']:>5}"
                f"{item['strategy']:<34}"
                f"{item['mean_probe_rate'] * 100:>9.2f}%"
                f"{item['mean_prevention_rate'] * 100:>11.2f}%"
                f"{item['mean_legitimate_total_friction']:>15.2f}"
                f"{item['mean_allocated_reviews']:>10.2f}"
                f"{item['mean_total_modeled_cost']:>16.2f}"
            )

        self.stdout.write("")
        self.stdout.write("Profile summaries")
        for summary in payload["profile_summaries"]:
            self.stdout.write(
                f"{summary['profile']}: "
                f"probes {summary['candidate_fewer_probe_cells']}/"
                f"{summary['total_cells']}; "
                f"prevention "
                f"{summary['prevention_better_cells']}/"
                f"{summary['prevention_equal_cells']}/"
                f"{summary['prevention_worse_cells']}; "
                f"friction lower/equal/higher "
                f"{summary['friction_lower_cells']}/"
                f"{summary['friction_equal_cells']}/"
                f"{summary['friction_higher_cells']}; "
                f"cost lower/equal/higher "
                f"{summary['cost_lower_cells']}/"
                f"{summary['cost_equal_cells']}/"
                f"{summary['cost_higher_cells']}; "
                f"worst prevention "
                f"{summary['minimum_prevention_delta']:.4f}; "
                f"worst cost "
                f"{summary['maximum_total_cost_delta']:.2f}; "
                f"mean review delta "
                f"{summary['mean_review_allocation_delta']:.2f}"
            )

        summary = payload["global_summary"]
        self.stdout.write("")
        self.stdout.write(
            "Global summary: "
            f"probes {summary['candidate_fewer_probe_cells']}/"
            f"{summary['total_cells']}; "
            f"prevention "
            f"{summary['prevention_better_cells']}/"
            f"{summary['prevention_equal_cells']}/"
            f"{summary['prevention_worse_cells']}; "
            f"cost "
            f"{summary['cost_lower_cells']}/"
            f"{summary['cost_equal_cells']}/"
            f"{summary['cost_higher_cells']}; "
            f"worst/best prevention "
            f"{summary['worst_prevention_delta']:.4f}/"
            f"{summary['best_prevention_delta']:.4f}; "
            f"worst/best cost "
            f"{summary['worst_total_cost_delta']:.2f}/"
            f"{summary['best_total_cost_delta']:.2f}; "
            f"largest positive review delta "
            f"{summary['largest_positive_review_allocation_delta']}"
        )
        self.stdout.write("")
        self.stdout.write(experiment["caveat"])
