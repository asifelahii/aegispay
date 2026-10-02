import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from experiments.services.probe_intervention_sensitivity import (
    ProbeInterventionSensitivityService,
)


class Command(BaseCommand):
    help = "Run EXP-03B intervention-assumption sensitivity."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=600)
        parser.add_argument("--seeds", default="7,21,42,84,126")
        parser.add_argument("--review-capacities", default="5,20")
        parser.add_argument(
            "--profiles",
            default=(
                "EQUAL_FAMILY,LEGITIMATE_DOMINANT,HARD_NEGATIVE_DOMINANT,"
                "SOCIAL_ENGINEERING_HEAVY,NETWORK_ABUSE_HEAVY"
            ),
        )
        parser.add_argument(
            "--assumptions",
            default=(
                "BASELINE,LOWER_PROTECTION,HIGHER_PROTECTION,"
                "HIGH_CUSTOMER_FRICTION,HIGH_OPERATIONS_COST,"
                "HIGH_REVIEW_COST,CONSERVATIVE_STRESS"
            ),
        )
        parser.add_argument("--output", default=None)

    def handle(self, *args, **options):
        try:
            seeds = self._integers(options["seeds"], "seeds")
            capacities = self._integers(
                options["review_capacities"], "review capacities"
            )
            profiles = self._strings(options["profiles"], "profiles")
            assumptions = self._strings(
                options["assumptions"], "assumptions"
            )
            result = ProbeInterventionSensitivityService().run(
                count=options["count"],
                profiles=profiles,
                seeds=seeds,
                review_capacities=capacities,
                assumptions=assumptions,
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
            self.stdout.write(self.style.SUCCESS(f"Saved EXP-03B to {path}"))

    @staticmethod
    def _integers(value, label):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"--{label.replace(' ', '-')} must not be empty.")
        parts = value.split(",")
        if any(not part.strip() for part in parts):
            raise ValueError(f"--{label.replace(' ', '-')} contains an empty value.")
        try:
            return [int(part.strip()) for part in parts]
        except ValueError as error:
            raise ValueError(
                f"--{label.replace(' ', '-')} must be a comma-separated list of integers."
            ) from error

    @staticmethod
    def _strings(value, label):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"--{label} must not be empty.")
        parts = [part.strip() for part in value.split(",")]
        if any(not part for part in parts):
            raise ValueError(f"--{label} contains an empty value.")
        return parts

    @staticmethod
    def _payload(result):
        def run_payload(run):
            return {
                "profile": run.profile,
                "family_counts": run.family_counts,
                "scenario_fingerprint": run.scenario_fingerprint,
                "seed": run.seed,
                "review_capacity": run.review_capacity,
                "assumption": run.assumption,
                "strategy": run.strategy,
                **run.metrics,
                "requested_action_counts": run.requested_action_counts,
                "effective_action_counts": run.effective_action_counts,
            }

        return {
            "experiment": {
                "name": "EXP-03B Intervention-Assumption Sensitivity",
                "scenario_count": result.count,
                "profiles": list(result.profiles),
                "seeds": list(result.seeds),
                "review_capacities": list(result.review_capacities),
                "assumptions": list(result.assumptions),
                "assumption_definitions": result.assumption_definitions,
                "controlled_cells": len(result.cells),
                "strategy_runs": len(result.runs),
                "candidate_status": "experimental_not_promoted",
                "scenario_source": "synthetic_prototype",
                "ground_truth_usage": "evaluation_only",
                "delta_convention": "candidate_minus_legacy",
                "caveat": (
                    "Intervention protection, customer-friction, and "
                    "operational-cost values in this experiment are prototype "
                    "sensitivity assumptions. They are not measured upay "
                    "intervention effectiveness, customer harm, or production "
                    "economics."
                ),
            },
            "runs": [run_payload(run) for run in result.runs],
            "cells": [
                {
                    "profile": cell.profile,
                    "seed": cell.seed,
                    "review_capacity": cell.review_capacity,
                    "assumption": cell.assumption,
                    "family_counts": cell.family_counts,
                    "scenario_fingerprint": cell.scenario_fingerprint,
                    "deltas": cell.deltas,
                }
                for cell in result.cells
            ],
            "global_assumption_aggregates": list(result.global_aggregates),
            "candidate_summaries": list(result.candidate_summaries),
            "global_candidate_summary": result.global_candidate_summary,
            "review_capacity_summary": list(result.review_capacity_summary),
            "decision_change_analysis": list(result.decision_change_analysis),
            "regressions": list(result.regressions),
        }

    def _print_result(self, payload):
        experiment = payload["experiment"]
        self.stdout.write("Metadata")
        for key in (
            "scenario_count", "profiles", "seeds", "review_capacities",
            "assumptions", "controlled_cells", "strategy_runs",
        ):
            self.stdout.write(f"{key}: {experiment[key]}")
        self.stdout.write("Global assumption table")
        for item in payload["global_assumption_aggregates"]:
            self.stdout.write(json.dumps(item, sort_keys=True))
        self.stdout.write("Candidate summary by assumption")
        for summary in payload["candidate_summaries"]:
            self.stdout.write(json.dumps(summary, sort_keys=True))
        self.stdout.write("Global candidate summary across all assumptions")
        self.stdout.write(
            json.dumps(
                payload["global_candidate_summary"],
                sort_keys=True,
            )
        )
        self.stdout.write("Review-capacity summary")
        for item in payload["review_capacity_summary"]:
            self.stdout.write(json.dumps(item, sort_keys=True))
        self.stdout.write("Decision-change table")
        for item in payload["decision_change_analysis"]:
            self.stdout.write(json.dumps(item, sort_keys=True))
        regression_metrics = {
            item["metric"] for item in payload["regressions"]
        }
        self.stdout.write(
            "Any candidate prevention regression: "
            + ("YES" if "prevention_rate" in regression_metrics else "NO")
        )
        self.stdout.write(
            "Any candidate legitimate-friction regression: "
            + (
                "YES"
                if "legitimate_total_friction" in regression_metrics
                else "NO"
            )
        )
        self.stdout.write(
            "Any candidate modeled-cost regression: "
            + ("YES" if "total_modeled_cost" in regression_metrics else "NO")
        )
        if payload["regressions"]:
            self.stdout.write("Affected regression cells")
            for item in payload["regressions"]:
                self.stdout.write(json.dumps(item, sort_keys=True))
        self.stdout.write(experiment["caveat"])
