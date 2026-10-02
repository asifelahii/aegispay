from dataclasses import dataclass
from enum import StrEnum

from interventions.services.policy import (
    InterventionProfile,
    MinimumEffectiveInterventionPolicy,
)


class InterventionAssumptionName(StrEnum):
    BASELINE = "BASELINE"
    LOWER_PROTECTION = "LOWER_PROTECTION"
    HIGHER_PROTECTION = "HIGHER_PROTECTION"
    HIGH_CUSTOMER_FRICTION = "HIGH_CUSTOMER_FRICTION"
    HIGH_OPERATIONS_COST = "HIGH_OPERATIONS_COST"
    HIGH_REVIEW_COST = "HIGH_REVIEW_COST"
    CONSERVATIVE_STRESS = "CONSERVATIVE_STRESS"


@dataclass(frozen=True, slots=True)
class InterventionAssumptionProfile:
    name: str
    description: str
    protection_multiplier: float
    friction_multiplier: float
    operations_multiplier: float
    human_review_operations_multiplier: float
    profiles: tuple[InterventionProfile, ...]

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "transforms": {
                "protection_multiplier": self.protection_multiplier,
                "friction_multiplier": self.friction_multiplier,
                "operations_multiplier": self.operations_multiplier,
                "human_review_operations_multiplier": (
                    self.human_review_operations_multiplier
                ),
            },
            "intervention_profiles": [
                {
                    "action": profile.action.value,
                    "protection_rate": profile.protection_rate,
                    "friction_cost": profile.friction_cost,
                    "operations_cost": profile.operations_cost,
                }
                for profile in self.profiles
            ],
        }


class ExperimentInterventionPolicy(
    MinimumEffectiveInterventionPolicy
):
    """Minimum-effective policy with experiment-local profile values."""

    def __init__(
        self,
        profiles: tuple[InterventionProfile, ...],
    ):
        self.PROFILES = profiles


class InterventionAssumptionBuilder:
    """Builds validated, experiment-only intervention assumptions."""

    DESCRIPTIONS = {
        InterventionAssumptionName.BASELINE: (
            "Current prototype intervention assumptions unchanged."
        ),
        InterventionAssumptionName.LOWER_PROTECTION: (
            "Non-zero intervention protection reduced by 20%."
        ),
        InterventionAssumptionName.HIGHER_PROTECTION: (
            "Non-zero intervention protection increased by 20%, capped at 0.95."
        ),
        InterventionAssumptionName.HIGH_CUSTOMER_FRICTION: (
            "Intervention customer-friction costs doubled."
        ),
        InterventionAssumptionName.HIGH_OPERATIONS_COST: (
            "Intervention operational costs doubled."
        ),
        InterventionAssumptionName.HIGH_REVIEW_COST: (
            "Human-review operational cost tripled."
        ),
        InterventionAssumptionName.CONSERVATIVE_STRESS: (
            "Protection reduced by 20%, friction increased by 50%, "
            "and operations cost doubled."
        ),
    }

    @classmethod
    def build(cls, name: str) -> InterventionAssumptionProfile:
        try:
            selected = InterventionAssumptionName(name)
        except ValueError as error:
            raise ValueError(
                f"Unknown intervention assumption profile: {name}."
            ) from error

        protection = 0.8 if selected in {
            InterventionAssumptionName.LOWER_PROTECTION,
            InterventionAssumptionName.CONSERVATIVE_STRESS,
        } else 1.2 if selected == (
            InterventionAssumptionName.HIGHER_PROTECTION
        ) else 1.0
        friction = 1.5 if selected == (
            InterventionAssumptionName.CONSERVATIVE_STRESS
        ) else 2.0 if selected == (
            InterventionAssumptionName.HIGH_CUSTOMER_FRICTION
        ) else 1.0
        operations = 2.0 if selected in {
            InterventionAssumptionName.HIGH_OPERATIONS_COST,
            InterventionAssumptionName.CONSERVATIVE_STRESS,
        } else 1.0
        review_operations = 3.0 if selected == (
            InterventionAssumptionName.HIGH_REVIEW_COST
        ) else 1.0

        profiles = []
        for baseline in MinimumEffectiveInterventionPolicy.PROFILES:
            if baseline.action.value == "ALLOW":
                profile = baseline
            else:
                profile = InterventionProfile(
                    action=baseline.action,
                    protection_rate=min(
                        1.0,
                        0.95,
                        baseline.protection_rate * protection,
                    ),
                    friction_cost=baseline.friction_cost * friction,
                    operations_cost=(
                        baseline.operations_cost
                        * operations
                        * (
                            review_operations
                            if baseline.action.value == "HUMAN_REVIEW"
                            else 1.0
                        )
                    ),
                )
            profiles.append(profile)

        result = InterventionAssumptionProfile(
            name=selected.value,
            description=cls.DESCRIPTIONS[selected],
            protection_multiplier=protection,
            friction_multiplier=friction,
            operations_multiplier=operations,
            human_review_operations_multiplier=review_operations,
            profiles=tuple(profiles),
        )
        cls.validate(result)
        return result

    @staticmethod
    def validate(profile: InterventionAssumptionProfile) -> None:
        for item in profile.profiles:
            if not 0.0 <= item.protection_rate <= 1.0:
                raise ValueError(
                    "Intervention protection rates must be between 0 and 1."
                )
            if item.friction_cost < 0 or item.operations_cost < 0:
                raise ValueError(
                    "Intervention friction and operations costs cannot be negative."
                )
            if item.action.value == "ALLOW" and (
                item.protection_rate != 0.0
                or item.friction_cost != 0.0
                or item.operations_cost != 0.0
            ):
                raise ValueError("ALLOW must have zero intervention costs and protection.")

    @classmethod
    def all(cls) -> tuple[InterventionAssumptionProfile, ...]:
        return tuple(cls.build(name.value) for name in InterventionAssumptionName)
