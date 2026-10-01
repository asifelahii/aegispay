from collections import Counter, defaultdict
from dataclasses import dataclass

from experiments.services.ablations import (
    NoContextProbeExperimentRunner,
)
from experiments.services.friction import (
    CustomerFrictionAccounting,
    FrictionAssumptions,
)
from experiments.services.runner import (
    AegisPayExperimentRunner,
)
from experiments.services.scenario_generator import (
    GeneratedScenario,
    ScenarioType,
)


@dataclass(frozen=True, slots=True)
class QuestionAuditCount:
    question_code: str
    count: int


@dataclass(frozen=True, slots=True)
class ContextProbeAuditRow:
    transaction_id: str
    scenario_type: str
    is_scam: bool

    context_requested: bool
    question_code: str | None

    base_risk_score: float
    full_final_risk_score: float
    risk_changed: bool

    no_probe_requested_action: str
    full_requested_action: str
    requested_action_changed: bool

    no_probe_effective_action: str
    full_effective_action: str
    effective_action_changed: bool

    incremental_prevented_scam_value: float
    legitimate_intervention_friction_delta: float
    legitimate_probe_friction: float
    operations_cost_delta: float

    modeled_cost_savings: float


@dataclass(frozen=True, slots=True)
class ScenarioProbeAudit:
    scenario_type: str
    total_transactions: int

    probes: int
    risk_changes: int
    requested_action_changes: int
    effective_action_changes: int

    incremental_prevented_scam_value: float
    legitimate_probe_friction: float
    modeled_cost_savings: float


@dataclass(frozen=True, slots=True)
class ContextProbeAuditSummary:
    total_transactions: int
    total_probes: int
    probe_rate: float

    risk_changed_probes: int
    risk_change_rate: float

    requested_action_changed_probes: int
    requested_action_change_rate: float

    effective_action_changed_probes: int
    effective_action_change_rate: float

    probes_without_requested_action_change: int

    incremental_prevented_scam_value: float

    legitimate_intervention_friction_delta: float
    legitimate_probe_friction: float
    operations_cost_delta: float

    net_modeled_cost_savings: float


@dataclass(frozen=True, slots=True)
class ContextProbeAuditResult:
    summary: ContextProbeAuditSummary

    by_scenario: tuple[
        ScenarioProbeAudit,
        ...
    ]

    question_counts: tuple[
        QuestionAuditCount,
        ...
    ]

    rows: tuple[
        ContextProbeAuditRow,
        ...
    ]


class ContextProbeAuditService:
    """
    Audits the effectiveness of Context Probe by comparing full
    AegisPay with the identical no-context-probe ablation.

    This service is diagnostic only.

    It does not change:
    - risk rules
    - thresholds
    - question selection
    - intervention policy
    - review capacity
    - synthetic scenarios
    """

    def __init__(
        self,
        no_probe_runner=None,
        full_runner=None,
        friction_assumptions=None,
    ):
        self.no_probe_runner = (
            no_probe_runner
            or NoContextProbeExperimentRunner()
        )

        self.full_runner = (
            full_runner
            or AegisPayExperimentRunner()
        )

        self.friction_assumptions = (
            friction_assumptions
            or FrictionAssumptions()
        )

        self.friction_accounting = (
            CustomerFrictionAccounting(
                assumptions=(
                    self.friction_assumptions
                )
            )
        )

    def audit(
        self,
        scenarios: list[
            GeneratedScenario
        ],
        *,
        review_capacity: int,
    ) -> ContextProbeAuditResult:
        if review_capacity < 0:
            raise ValueError(
                "Review capacity cannot be negative."
            )

        no_probe = (
            self.no_probe_runner.run(
                scenarios,
                review_capacity=review_capacity,
            )
        )

        full = (
            self.full_runner.run(
                scenarios,
                review_capacity=review_capacity,
            )
        )

        no_probe_by_id = {
            outcome.transaction_id: outcome
            for outcome
            in no_probe.outcomes
        }

        full_by_id = {
            outcome.transaction_id: outcome
            for outcome
            in full.outcomes
        }

        if (
            set(no_probe_by_id)
            != set(full_by_id)
        ):
            raise ValueError(
                "Ablation and full experiment "
                "transaction IDs do not match."
            )

        rows = []

        for full_outcome in full.outcomes:
            transaction_id = (
                full_outcome.transaction_id
            )

            no_probe_outcome = (
                no_probe_by_id[
                    transaction_id
                ]
            )

            if (
                no_probe_outcome.is_scam
                != full_outcome.is_scam
            ):
                raise ValueError(
                    "Ground truth mismatch between "
                    "ablation runs."
                )

            if (
                abs(
                    no_probe_outcome.base_risk_score
                    - full_outcome.base_risk_score
                )
                > 1e-9
            ):
                raise ValueError(
                    "Base-risk mismatch between "
                    "ablation runs."
                )

            risk_changed = (
                full_outcome.context_requested
                and abs(
                    full_outcome.final_risk_score
                    - full_outcome.base_risk_score
                )
                > 1e-9
            )

            requested_action_changed = (
                full_outcome.context_requested
                and (
                    no_probe_outcome.requested_action
                    != full_outcome.requested_action
                )
            )

            effective_action_changed = (
                full_outcome.context_requested
                and (
                    no_probe_outcome.effective_action
                    != full_outcome.effective_action
                )
            )

            if full_outcome.is_scam:
                prevented_delta = (
                    full_outcome.prevented_scam_value
                    - no_probe_outcome.prevented_scam_value
                )

                intervention_friction_delta = 0.0
                probe_friction = 0.0

            else:
                prevented_delta = 0.0

                intervention_friction_delta = (
                    full_outcome.friction_cost
                    - no_probe_outcome.friction_cost
                )

                probe_friction = (
                    self.friction_assumptions.context_probe_cost
                    if full_outcome.context_requested
                    else 0.0
                )

            operations_delta = (
                full_outcome.operations_cost
                - no_probe_outcome.operations_cost
            )

            no_probe_cost = (
                no_probe_outcome.residual_scam_loss
                + no_probe_outcome.operations_cost
            )

            full_cost = (
                full_outcome.residual_scam_loss
                + full_outcome.operations_cost
            )

            if not full_outcome.is_scam:
                no_probe_cost += (
                    no_probe_outcome.friction_cost
                )

                full_cost += (
                    full_outcome.friction_cost
                    + probe_friction
                )

            modeled_cost_savings = (
                no_probe_cost
                - full_cost
            )

            rows.append(
                ContextProbeAuditRow(
                    transaction_id=transaction_id,
                    scenario_type=(
                        full_outcome.scenario_type
                    ),
                    is_scam=(
                        full_outcome.is_scam
                    ),
                    context_requested=(
                        full_outcome.context_requested
                    ),
                    question_code=(
                        full_outcome.context_question_code
                    ),
                    base_risk_score=(
                        full_outcome.base_risk_score
                    ),
                    full_final_risk_score=(
                        full_outcome.final_risk_score
                    ),
                    risk_changed=(
                        risk_changed
                    ),
                    no_probe_requested_action=(
                        no_probe_outcome.requested_action.value
                    ),
                    full_requested_action=(
                        full_outcome.requested_action.value
                    ),
                    requested_action_changed=(
                        requested_action_changed
                    ),
                    no_probe_effective_action=(
                        no_probe_outcome.effective_action.value
                    ),
                    full_effective_action=(
                        full_outcome.effective_action.value
                    ),
                    effective_action_changed=(
                        effective_action_changed
                    ),
                    incremental_prevented_scam_value=round(
                        prevented_delta,
                        2,
                    ),
                    legitimate_intervention_friction_delta=round(
                        intervention_friction_delta,
                        2,
                    ),
                    legitimate_probe_friction=round(
                        probe_friction,
                        2,
                    ),
                    operations_cost_delta=round(
                        operations_delta,
                        2,
                    ),
                    modeled_cost_savings=round(
                        modeled_cost_savings,
                        2,
                    ),
                )
            )

        summary = self._summarize(
            rows=rows,
            no_probe=no_probe,
            full=full,
        )

        by_scenario = (
            self._scenario_breakdown(
                rows
            )
        )

        question_counter = Counter(
            row.question_code
            for row in rows
            if (
                row.context_requested
                and row.question_code
                is not None
            )
        )

        question_counts = tuple(
            QuestionAuditCount(
                question_code=code,
                count=count,
            )
            for (
                code,
                count,
            ) in sorted(
                question_counter.items()
            )
        )

        return ContextProbeAuditResult(
            summary=summary,
            by_scenario=by_scenario,
            question_counts=question_counts,
            rows=tuple(rows),
        )

    def _summarize(
        self,
        *,
        rows,
        no_probe,
        full,
    ) -> ContextProbeAuditSummary:
        probed = [
            row
            for row in rows
            if row.context_requested
        ]

        total_probes = len(
            probed
        )

        risk_changed = sum(
            1
            for row in probed
            if row.risk_changed
        )

        requested_action_changed = sum(
            1
            for row in probed
            if row.requested_action_changed
        )

        effective_action_changed = sum(
            1
            for row in probed
            if row.effective_action_changed
        )

        if total_probes > 0:
            probe_rate = (
                total_probes
                / len(rows)
            )

            risk_change_rate = (
                risk_changed
                / total_probes
            )

            requested_action_change_rate = (
                requested_action_changed
                / total_probes
            )

            effective_action_change_rate = (
                effective_action_changed
                / total_probes
            )
        else:
            probe_rate = 0.0
            risk_change_rate = 0.0
            requested_action_change_rate = 0.0
            effective_action_change_rate = 0.0

        no_probe_friction = (
            self.friction_accounting.calculate(
                no_probe
            )
        )

        full_friction = (
            self.friction_accounting.calculate(
                full
            )
        )

        no_probe_total_cost = (
            no_probe.summary.residual_scam_loss
            + no_probe_friction.legitimate_total_customer_friction_cost
            + no_probe.summary.operations_cost
        )

        full_total_cost = (
            full.summary.residual_scam_loss
            + full_friction.legitimate_total_customer_friction_cost
            + full.summary.operations_cost
        )

        return ContextProbeAuditSummary(
            total_transactions=len(
                rows
            ),
            total_probes=(
                total_probes
            ),
            probe_rate=round(
                probe_rate,
                4,
            ),
            risk_changed_probes=(
                risk_changed
            ),
            risk_change_rate=round(
                risk_change_rate,
                4,
            ),
            requested_action_changed_probes=(
                requested_action_changed
            ),
            requested_action_change_rate=round(
                requested_action_change_rate,
                4,
            ),
            effective_action_changed_probes=(
                effective_action_changed
            ),
            effective_action_change_rate=round(
                effective_action_change_rate,
                4,
            ),
            probes_without_requested_action_change=(
                total_probes
                - requested_action_changed
            ),
            incremental_prevented_scam_value=round(
                (
                    full.summary.prevented_scam_value
                    - no_probe.summary.prevented_scam_value
                ),
                2,
            ),
            legitimate_intervention_friction_delta=round(
                (
                    full_friction.legitimate_intervention_friction_cost
                    - no_probe_friction.legitimate_intervention_friction_cost
                ),
                2,
            ),
            legitimate_probe_friction=round(
                full_friction.legitimate_context_probe_friction_cost,
                2,
            ),
            operations_cost_delta=round(
                (
                    full.summary.operations_cost
                    - no_probe.summary.operations_cost
                ),
                2,
            ),
            net_modeled_cost_savings=round(
                (
                    no_probe_total_cost
                    - full_total_cost
                ),
                2,
            ),
        )

    @staticmethod
    def _scenario_breakdown(
        rows,
    ) -> tuple[
        ScenarioProbeAudit,
        ...
    ]:
        grouped = defaultdict(
            list
        )

        for row in rows:
            grouped[
                row.scenario_type
            ].append(row)

        order = {
            scenario_type.value: index
            for (
                index,
                scenario_type,
            ) in enumerate(
                ScenarioType
            )
        }

        result = []

        for scenario_type in sorted(
            grouped,
            key=lambda value: (
                order.get(
                    value,
                    999,
                )
            ),
        ):
            group = grouped[
                scenario_type
            ]

            result.append(
                ScenarioProbeAudit(
                    scenario_type=scenario_type,
                    total_transactions=len(
                        group
                    ),
                    probes=sum(
                        1
                        for row in group
                        if row.context_requested
                    ),
                    risk_changes=sum(
                        1
                        for row in group
                        if row.risk_changed
                    ),
                    requested_action_changes=sum(
                        1
                        for row in group
                        if row.requested_action_changed
                    ),
                    effective_action_changes=sum(
                        1
                        for row in group
                        if row.effective_action_changed
                    ),
                    incremental_prevented_scam_value=round(
                        sum(
                            row.incremental_prevented_scam_value
                            for row in group
                        ),
                        2,
                    ),
                    legitimate_probe_friction=round(
                        sum(
                            row.legitimate_probe_friction
                            for row in group
                        ),
                        2,
                    ),
                    modeled_cost_savings=round(
                        sum(
                            row.modeled_cost_savings
                            for row in group
                        ),
                        2,
                    ),
                )
            )

        return tuple(
            result
        )