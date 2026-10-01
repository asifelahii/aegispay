import json
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from experiments.services.probe_audit import (
    ContextProbeAuditService,
)
from experiments.services.scenario_generator import (
    SyntheticScenarioGenerator,
)


class Command(BaseCommand):
    help = (
        "Audit how often AegisPay Context Probe "
        "actually changes risk or intervention decisions."
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
            ContextProbeAuditService().audit(
                scenarios,
                review_capacity=review_capacity,
            )
        )

        payload = self._payload(
            result=result,
            count=count,
            seed=seed,
            review_capacity=review_capacity,
        )

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
                    f"Saved Context Probe audit to "
                    f"{path}"
                )
            )

    @staticmethod
    def _payload(
        *,
        result,
        count,
        seed,
        review_capacity,
    ):
        summary = result.summary

        return {
            "experiment": {
                "name": (
                    "AegisPay Context Probe "
                    "Effectiveness Audit"
                ),
                "scenario_count": count,
                "seed": seed,
                "review_capacity": (
                    review_capacity
                ),
                "scenario_source": (
                    "synthetic_prototype"
                ),
                "diagnostic_only": True,
            },
            "summary": {
                "total_transactions": (
                    summary.total_transactions
                ),
                "total_probes": (
                    summary.total_probes
                ),
                "probe_rate": (
                    summary.probe_rate
                ),
                "risk_changed_probes": (
                    summary.risk_changed_probes
                ),
                "risk_change_rate": (
                    summary.risk_change_rate
                ),
                "requested_action_changed_probes": (
                    summary.requested_action_changed_probes
                ),
                "requested_action_change_rate": (
                    summary.requested_action_change_rate
                ),
                "effective_action_changed_probes": (
                    summary.effective_action_changed_probes
                ),
                "effective_action_change_rate": (
                    summary.effective_action_change_rate
                ),
                "probes_without_requested_action_change": (
                    summary.probes_without_requested_action_change
                ),
                "incremental_prevented_scam_value": (
                    summary.incremental_prevented_scam_value
                ),
                "legitimate_intervention_friction_delta": (
                    summary.legitimate_intervention_friction_delta
                ),
                "legitimate_probe_friction": (
                    summary.legitimate_probe_friction
                ),
                "operations_cost_delta": (
                    summary.operations_cost_delta
                ),
                "net_modeled_cost_savings": (
                    summary.net_modeled_cost_savings
                ),
            },
            "question_counts": [
                {
                    "question_code": (
                        item.question_code
                    ),
                    "count": item.count,
                }
                for item
                in result.question_counts
            ],
            "scenario_breakdown": [
                {
                    "scenario_type": (
                        item.scenario_type
                    ),
                    "total_transactions": (
                        item.total_transactions
                    ),
                    "probes": item.probes,
                    "risk_changes": (
                        item.risk_changes
                    ),
                    "requested_action_changes": (
                        item.requested_action_changes
                    ),
                    "effective_action_changes": (
                        item.effective_action_changes
                    ),
                    "incremental_prevented_scam_value": (
                        item.incremental_prevented_scam_value
                    ),
                    "legitimate_probe_friction": (
                        item.legitimate_probe_friction
                    ),
                    "modeled_cost_savings": (
                        item.modeled_cost_savings
                    ),
                }
                for item
                in result.by_scenario
            ],
        }

    def _print_result(
        self,
        payload,
    ):
        summary = payload[
            "summary"
        ]

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "AegisPay Context Probe "
                "Effectiveness Audit"
            )
        )

        self.stdout.write(
            f"Transactions: "
            f"{summary['total_transactions']}"
        )

        self.stdout.write(
            f"Probes: "
            f"{summary['total_probes']} "
            f"({summary['probe_rate'] * 100:.2f}%)"
        )

        self.stdout.write(
            f"Risk-changing probes: "
            f"{summary['risk_changed_probes']} "
            f"({summary['risk_change_rate'] * 100:.2f}%)"
        )

        self.stdout.write(
            f"Requested-action-changing probes: "
            f"{summary['requested_action_changed_probes']} "
            f"("
            f"{summary['requested_action_change_rate'] * 100:.2f}"
            f"%)"
        )

        self.stdout.write(
            f"Effective-action-changing probes: "
            f"{summary['effective_action_changed_probes']} "
            f"("
            f"{summary['effective_action_change_rate'] * 100:.2f}"
            f"%)"
        )

        self.stdout.write("")

        header = (
            f"{'Scenario':<26}"
            f"{'N':>5}"
            f"{'Probe':>7}"
            f"{'Risk Δ':>8}"
            f"{'ReqAct Δ':>10}"
            f"{'EffAct Δ':>10}"
            f"{'Prevent +':>13}"
            f"{'Probe Fric.':>13}"
            f"{'Cost Save':>13}"
        )

        self.stdout.write(
            header
        )

        self.stdout.write(
            "-" * len(header)
        )

        for row in payload[
            "scenario_breakdown"
        ]:
            self.stdout.write(
                f"{row['scenario_type']:<26}"
                f"{row['total_transactions']:>5}"
                f"{row['probes']:>7}"
                f"{row['risk_changes']:>8}"
                f"{row['requested_action_changes']:>10}"
                f"{row['effective_action_changes']:>10}"
                f"{row['incremental_prevented_scam_value']:>13.2f}"
                f"{row['legitimate_probe_friction']:>13.2f}"
                f"{row['modeled_cost_savings']:>13.2f}"
            )

        self.stdout.write("")

        self.stdout.write(
            f"Incremental prevented scam value: "
            f"{summary['incremental_prevented_scam_value']:.2f}"
        )

        self.stdout.write(
            f"Legitimate probe friction: "
            f"{summary['legitimate_probe_friction']:.2f}"
        )

        self.stdout.write(
            f"Net modeled cost savings: "
            f"{summary['net_modeled_cost_savings']:.2f}"
        )

        self.stdout.write("")

        self.stdout.write(
            "Diagnostic only: no Context Probe or "
            "intervention-policy behavior was changed."
        )