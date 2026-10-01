import json
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from experiments.services.probe_robustness import (
    ProbeRobustnessResult,
    ProbeRobustnessService,
)


class Command(BaseCommand):
    help = (
        "Validate Context Probe selectivity across seeds "
        "and review capacities."
    )

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=600)
        parser.add_argument(
            "--seeds",
            type=str,
            default="7,21,42,84,126",
        )
        parser.add_argument(
            "--review-capacities",
            type=str,
            default="0,5,10,20,40",
        )
        parser.add_argument("--output", type=str, default=None)

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
            result = ProbeRobustnessService().run(
                count=options["count"],
                seeds=seeds,
                review_capacities=capacities,
            )
        except ValueError as error:
            raise CommandError(str(error)) from error

        payload = self._payload(result)
        self._print_result(payload)

        output = options["output"]
        if output:
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Saved Context Probe robustness result to {path}"
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
            return [
                int(part.strip())
                for part in parts
            ]
        except ValueError as error:
            raise ValueError(
                f"--{label.replace(' ', '-')} must be a comma-separated "
                "list of integers."
            ) from error

    @staticmethod
    def _payload(result: ProbeRobustnessResult):
        return {
            "experiment": {
                "name": (
                    "AegisPay Context Probe Robustness Validation"
                ),
                "scenario_count": result.count,
                "seeds": list(result.seeds),
                "review_capacities": list(
                    result.review_capacities
                ),
                "controlled_comparisons": len(result.cells),
                "scenario_source": "synthetic_prototype",
                "ground_truth_usage": "evaluation_only",
                "candidate_status": "experimental_not_promoted",
                "standard_deviation": "population",
                "delta_convention": "candidate_minus_legacy",
                "caveat": (
                    "This is a synthetic prototype robustness experiment "
                    "across random seeds and review capacities. It does "
                    "not establish real upay fraud prevalence, production "
                    "performance, or causal intervention effectiveness."
                ),
                "scenario_mixture_limitation": (
                    "The scenario generator uses a deterministic "
                    "round-robin scenario-family mixture; seed changes "
                    "randomized transaction values rather than prevalence."
                ),
            },
            "runs": [
                {
                    key: getattr(run, key)
                    for key in (
                        "seed",
                        "review_capacity",
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
                }
                for run in result.runs
            ],
            "cells": [
                {
                    "seed": cell.seed,
                    "review_capacity": cell.review_capacity,
                    "scenario_fingerprint": (
                        cell.scenario_fingerprint
                    ),
                }
                for cell in result.cells
            ],
            "capacity_aggregates": [
                {
                    key: getattr(aggregate, key)
                    for key in (
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
                }
                for aggregate in result.aggregates
            ],
            "robustness_summary": {
                key: getattr(result.summary, key)
                for key in (
                    "total_cells",
                    "candidate_fewer_probe_cells",
                    "candidate_prevention_better_cells",
                    "candidate_prevention_equal_cells",
                    "candidate_prevention_worse_cells",
                    "candidate_total_cost_better_cells",
                    "candidate_total_cost_equal_cells",
                    "candidate_total_cost_worse_cells",
                    "candidate_legitimate_friction_better_cells",
                    "worst_prevention_delta",
                    "best_prevention_delta",
                    "worst_total_cost_delta",
                    "best_total_cost_delta",
                )
            },
        }

    def _print_result(self, payload):
        experiment = payload["experiment"]
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "AegisPay Context Probe Robustness Validation"
            )
        )
        self.stdout.write(
            f"Scenarios per comparison: "
            f"{experiment['scenario_count']}"
        )
        self.stdout.write(
            f"Seeds: {','.join(map(str, experiment['seeds']))}"
        )
        self.stdout.write(
            "Capacities: "
            f"{','.join(map(str, experiment['review_capacities']))}"
        )
        self.stdout.write(
            f"Controlled comparisons: "
            f"{experiment['controlled_comparisons']}"
        )
        self.stdout.write("")

        header = (
            f"{'Capacity':>10}"
            f"{'Strategy':<34}"
            f"{'Mean Probe %':>14}"
            f"{'Mean Prevent %':>16}"
            f"{'Mean Legit Fric.':>19}"
            f"{'Mean Reviews':>14}"
            f"{'Mean Total Cost':>18}"
        )
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for item in payload["capacity_aggregates"]:
            self.stdout.write(
                f"{item['review_capacity']:>10}"
                f"{item['strategy']:<34}"
                f"{item['mean_probe_rate'] * 100:>13.2f}%"
                f"{item['mean_prevention_rate'] * 100:>15.2f}%"
                f"{item['mean_legitimate_total_friction']:>19.2f}"
                f"{item['mean_allocated_reviews']:>14.2f}"
                f"{item['mean_total_modeled_cost']:>18.2f}"
            )

        summary = payload["robustness_summary"]
        self.stdout.write("")
        self.stdout.write("Robustness summary")
        self.stdout.write(
            f"Fewer-probe cells: "
            f"{summary['candidate_fewer_probe_cells']}/"
            f"{summary['total_cells']}"
        )
        self.stdout.write(
            "Prevention better/equal/worse: "
            f"{summary['candidate_prevention_better_cells']}/"
            f"{summary['candidate_prevention_equal_cells']}/"
            f"{summary['candidate_prevention_worse_cells']}"
        )
        self.stdout.write(
            "Total cost better/equal/worse: "
            f"{summary['candidate_total_cost_better_cells']}/"
            f"{summary['candidate_total_cost_equal_cells']}/"
            f"{summary['candidate_total_cost_worse_cells']}"
        )
        self.stdout.write(
            f"Legitimate-friction-better cells: "
            f"{summary['candidate_legitimate_friction_better_cells']}"
        )
        self.stdout.write(
            f"Prevention delta worst/best: "
            f"{summary['worst_prevention_delta']:.4f}/"
            f"{summary['best_prevention_delta']:.4f}"
        )
        self.stdout.write(
            f"Total-cost delta worst/best: "
            f"{summary['worst_total_cost_delta']:.2f}/"
            f"{summary['best_total_cost_delta']:.2f}"
        )
        self.stdout.write("")
        self.stdout.write(
            experiment["caveat"]
        )
