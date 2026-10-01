import json
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from experiments.services.comparison import (
    PolicyComparisonService,
)
from experiments.services.scenario_generator import (
    SyntheticScenarioGenerator,
)


class Command(BaseCommand):
    help = (
        "Run a reproducible AegisPay policy-comparison "
        "experiment using synthetic scenarios."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--count",
            type=int,
            default=600,
            help=(
                "Number of synthetic scenarios to generate. "
                "Default: 600."
            ),
        )

        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help=(
                "Random seed used by the synthetic scenario "
                "generator. Default: 42."
            ),
        )

        parser.add_argument(
            "--review-capacity",
            type=int,
            default=20,
            help=(
                "Maximum number of human reviews available "
                "for each compared strategy. Default: 20."
            ),
        )

        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help=(
                "Optional JSON output path, for example "
                "'artifacts/experiment_seed42.json'."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        count = options["count"]
        seed = options["seed"]

        review_capacity = (
            options["review_capacity"]
        )

        output = options["output"]

        if count <= 0:
            raise CommandError(
                "--count must be greater than zero."
            )

        if review_capacity < 0:
            raise CommandError(
                "--review-capacity cannot be negative."
            )

        start_time = datetime(
            2026,
            10,
            1,
            0,
            0,
            tzinfo=UTC,
        )

        generator = (
            SyntheticScenarioGenerator(
                seed=seed
            )
        )

        scenarios = generator.generate(
            count=count,
            start_time=start_time,
        )

        comparison = (
            PolicyComparisonService().compare(
                scenarios,
                review_capacity=review_capacity,
            )
        )

        payload = self._build_payload(
            comparison=comparison,
            count=count,
            seed=seed,
            start_time=start_time,
        )

        self._print_results(
            payload
        )

        if output:
            output_path = Path(
                output
            )

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            output_path.write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Saved experiment result to "
                    f"{output_path}"
                )
            )

    @staticmethod
    def _build_payload(
        *,
        comparison,
        count,
        seed,
        start_time,
    ):
        return {
            "experiment": {
                "name": (
                    "AegisPay Synthetic Policy Comparison"
                ),
                "scenario_source": (
                    "synthetic_prototype"
                ),
                "ground_truth_usage": (
                    "evaluation_only"
                ),
                "scenario_count": count,
                "seed": seed,
                "review_capacity": (
                    comparison.review_capacity
                ),
                "start_time": (
                    start_time.isoformat()
                ),
                "friction_assumptions": {
                    "context_probe_cost": 25.0,
                    "status": (
                        "prototype_simulation_assumption"
                    ),
                },
            },
            "strategies": [
                {
                    "strategy": (
                        metrics.strategy
                    ),
                    "total_scenarios": (
                        metrics.total_scenarios
                    ),
                    "scam_scenarios": (
                        metrics.scam_scenarios
                    ),
                    "legitimate_scenarios": (
                        metrics.legitimate_scenarios
                    ),
                    "context_probes": (
                        metrics.context_probes
                    ),
                    "requested_reviews": (
                        metrics.requested_reviews
                    ),
                    "allocated_reviews": (
                        metrics.allocated_reviews
                    ),
                    "total_scam_value": (
                        metrics.total_scam_value
                    ),
                    "prevented_scam_value": (
                        metrics.prevented_scam_value
                    ),
                    "residual_scam_loss": (
                        metrics.residual_scam_loss
                    ),
                    "prevention_rate": (
                        metrics.prevention_rate
                    ),
                    "legitimate_friction_cost": (
                        metrics.legitimate_friction_cost
                    ),
                    "legitimate_context_probe_friction_cost": (
                        metrics.legitimate_context_probe_friction_cost
                    ),
                    "legitimate_total_customer_friction_cost": (
                        metrics.legitimate_total_customer_friction_cost
                    ),
                    "operations_cost": (
                        metrics.operations_cost
                    ),
                    "total_modeled_cost": (
                        metrics.total_modeled_cost
                    ),
                    "protected_value_per_review": (
                        metrics.protected_value_per_review
                    ),
                    "friction_per_legitimate_transaction": (
                        metrics.friction_per_legitimate_transaction
                    ),
                }
                for metrics
                in comparison.strategies
            ],
        }

    def _print_results(
        self,
        payload,
    ):
        experiment = (
            payload["experiment"]
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "AegisPay Policy Comparison"
            )
        )

        self.stdout.write(
            f"Scenarios: "
            f"{experiment['scenario_count']}"
        )

        self.stdout.write(
            f"Seed: "
            f"{experiment['seed']}"
        )

        self.stdout.write(
            f"Review capacity: "
            f"{experiment['review_capacity']}"
        )

        self.stdout.write("")

        header = (
            f"{'Strategy':<20}"
            f"{'Prevent %':>12}"
            f"{'Residual':>14}"
            f"{'Interv Fric.':>14}"
            f"{'Probe Fric.':>13}"
            f"{'Total Fric.':>13}"
            f"{'Reviews':>10}"
            f"{'Total Cost':>14}"
        )

        self.stdout.write(
            header
        )

        self.stdout.write(
            "-" * len(header)
        )

        for metrics in payload[
            "strategies"
        ]:
            self.stdout.write(
                f"{metrics['strategy']:<20}"
                f"{metrics['prevention_rate'] * 100:>11.2f}%"
                f"{metrics['residual_scam_loss']:>14.2f}"
                f"{metrics['legitimate_friction_cost']:>14.2f}"
                f"{metrics['legitimate_context_probe_friction_cost']:>13.2f}"
                f"{metrics['legitimate_total_customer_friction_cost']:>13.2f}"
                f"{metrics['allocated_reviews']:>10}"
                f"{metrics['total_modeled_cost']:>14.2f}"
            )

        self.stdout.write("")

        self.stdout.write(
            "Important: intervention-effect, intervention-friction, "
            "and Context Probe friction values are prototype "
            "simulation assumptions, not measured upay production "
            "outcomes."
        )