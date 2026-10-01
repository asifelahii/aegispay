from datetime import UTC, datetime

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from experiments.services.diagnostics import (
    ExperimentDiagnosticsService,
)
from experiments.services.scenario_generator import (
    SyntheticScenarioGenerator,
)


class Command(BaseCommand):
    help = (
        "Show scenario-level diagnostics for "
        "AegisPay and comparison policies."
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
            ExperimentDiagnosticsService().analyze(
                scenarios,
                review_capacity=review_capacity,
            )
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "AegisPay Scenario Diagnostics"
            )
        )

        self.stdout.write(
            f"Scenarios: {count}"
        )

        self.stdout.write(
            f"Seed: {seed}"
        )

        self.stdout.write(
            f"Review capacity: "
            f"{review_capacity}"
        )

        self.stdout.write("")

        header = (
            f"{'Strategy':<18}"
            f"{'Scenario':<26}"
            f"{'N':>5}"
            f"{'Base':>8}"
            f"{'Final':>8}"
            f"{'Probe':>7}"
            f"{'Review':>8}"
            f"{'Legit Fric.':>14}"
        )

        self.stdout.write(
            header
        )

        self.stdout.write(
            "-" * len(header)
        )

        for row in result.rows:
            self.stdout.write(
                f"{row.strategy:<18}"
                f"{row.scenario_type:<26}"
                f"{row.total_scenarios:>5}"
                f"{row.average_base_risk:>8.2f}"
                f"{row.average_final_risk:>8.2f}"
                f"{row.context_probes:>7}"
                f"{row.allocated_reviews:>8}"
                f"{row.legitimate_friction_cost:>14.2f}"
            )

            actions = ", ".join(
                (
                    f"{item.action}="
                    f"{item.count}"
                )
                for item
                in row.action_counts
            )

            self.stdout.write(
                f"  Actions: {actions}"
            )

            if row.question_counts:
                questions = ", ".join(
                    (
                        f"{item.question_code}="
                        f"{item.count}"
                    )
                    for item
                    in row.question_counts
                )

                self.stdout.write(
                    f"  Questions: {questions}"
                )

        self.stdout.write("")
        self.stdout.write(
            "Diagnostic only: no policy "
            "parameters were changed."
        )