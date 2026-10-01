import json
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from experiments.services.ablations import (
    ContextProbeAblationService,
)
from experiments.services.scenario_generator import (
    SyntheticScenarioGenerator,
)


class Command(BaseCommand):
    help = (
        "Compare full AegisPay with an AegisPay "
        "ablation that removes Context Probe."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--count",
            type=int,
            default=600,
        )

        parser.add_argument(
            "--seed",
            type=int,
            default=42,
        )

        parser.add_argument(
            "--review-capacity",
            type=int,
            default=20,
        )

        parser.add_argument(
            "--output",
            type=str,
            default=None,
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

        scenarios = (
            SyntheticScenarioGenerator(
                seed=seed
            ).generate(
                count=count,
                start_time=datetime(
                    2026,
                    10,
                    1,
                    tzinfo=UTC,
                ),
            )
        )

        result = (
            ContextProbeAblationService().compare(
                scenarios,
                review_capacity=review_capacity,
            )
        )

        payload = {
            "experiment": {
                "name": (
                    "AegisPay Context Probe Ablation"
                ),
                "scenario_count": count,
                "seed": seed,
                "review_capacity": (
                    review_capacity
                ),
                "scenario_source": (
                    "synthetic_prototype"
                ),
                "context_probe_cost": 25.0,
            },
            "strategies": [
                {
                    "strategy": (
                        item.strategy
                    ),
                    "prevention_rate": (
                        item.prevention_rate
                    ),
                    "prevented_scam_value": (
                        item.prevented_scam_value
                    ),
                    "residual_scam_loss": (
                        item.residual_scam_loss
                    ),
                    "context_probes": (
                        item.context_probes
                    ),
                    "legitimate_intervention_friction": (
                        item.legitimate_intervention_friction
                    ),
                    "legitimate_probe_friction": (
                        item.legitimate_probe_friction
                    ),
                    "legitimate_total_friction": (
                        item.legitimate_total_friction
                    ),
                    "requested_reviews": (
                        item.requested_reviews
                    ),
                    "allocated_reviews": (
                        item.allocated_reviews
                    ),
                    "operations_cost": (
                        item.operations_cost
                    ),
                    "total_modeled_cost": (
                        item.total_modeled_cost
                    ),
                }
                for item
                in result.strategies
            ],
        }

        self._print_result(
            payload
        )

        if output:
            path = Path(
                output
            )

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

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
                    f"Saved ablation result to "
                    f"{path}"
                )
            )

    def _print_result(
        self,
        payload,
    ):
        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "AegisPay Context Probe Ablation"
            )
        )

        experiment = (
            payload["experiment"]
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
            f"{'Strategy':<28}"
            f"{'Prevent %':>12}"
            f"{'Residual':>14}"
            f"{'Probe':>9}"
            f"{'Total Fric.':>14}"
            f"{'Reviews':>10}"
            f"{'Total Cost':>14}"
        )

        self.stdout.write(
            header
        )

        self.stdout.write(
            "-" * len(header)
        )

        for item in payload[
            "strategies"
        ]:
            self.stdout.write(
                f"{item['strategy']:<28}"
                f"{item['prevention_rate'] * 100:>11.2f}%"
                f"{item['residual_scam_loss']:>14.2f}"
                f"{item['context_probes']:>9}"
                f"{item['legitimate_total_friction']:>14.2f}"
                f"{item['allocated_reviews']:>10}"
                f"{item['total_modeled_cost']:>14.2f}"
            )

        self.stdout.write("")

        self.stdout.write(
            "Ablation only: no risk weights, thresholds, "
            "scenario definitions, or intervention assumptions "
            "were changed."
        )