from dataclasses import dataclass

from experiments.services.runner import ExperimentResult


@dataclass(frozen=True, slots=True)
class FrictionAssumptions:
    """
    Prototype customer-friction assumptions.

    These values are simulation parameters only.
    They are not measured upay production values.
    """

    context_probe_cost: float = 25.0

    def __post_init__(self):
        if self.context_probe_cost < 0:
            raise ValueError(
                "Context-probe friction cost cannot be negative."
            )


@dataclass(frozen=True, slots=True)
class CustomerFrictionBreakdown:
    legitimate_context_probes: int

    legitimate_intervention_friction_cost: float
    legitimate_context_probe_friction_cost: float
    legitimate_total_customer_friction_cost: float


class CustomerFrictionAccounting:
    """
    Separates intervention friction from Context Probe friction.

    Existing ScenarioOutcome.friction_cost represents intervention
    friction only.

    A context question is an additional customer interaction and must
    therefore be accounted for separately when comparing strategies.
    """

    def __init__(
        self,
        assumptions: FrictionAssumptions | None = None,
    ):
        self.assumptions = (
            assumptions
            or FrictionAssumptions()
        )

    def calculate(
        self,
        result: ExperimentResult,
    ) -> CustomerFrictionBreakdown:
        legitimate_outcomes = [
            outcome
            for outcome in result.outcomes
            if not outcome.is_scam
        ]

        legitimate_context_probes = sum(
            1
            for outcome in legitimate_outcomes
            if outcome.context_requested
        )

        intervention_friction = sum(
            outcome.friction_cost
            for outcome in legitimate_outcomes
        )

        context_probe_friction = (
            legitimate_context_probes
            * self.assumptions.context_probe_cost
        )

        total_customer_friction = (
            intervention_friction
            + context_probe_friction
        )

        return CustomerFrictionBreakdown(
            legitimate_context_probes=(
                legitimate_context_probes
            ),
            legitimate_intervention_friction_cost=round(
                intervention_friction,
                2,
            ),
            legitimate_context_probe_friction_cost=round(
                context_probe_friction,
                2,
            ),
            legitimate_total_customer_friction_cost=round(
                total_customer_friction,
                2,
            ),
        )