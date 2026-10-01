from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import random

from experiments.services.scenario_generator import (
    GeneratedScenario,
    ScenarioType,
    SyntheticScenarioGenerator,
)


@dataclass(frozen=True, slots=True)
class ScenarioMixtureProfile:
    name: str
    weights: dict[ScenarioType, int]


@dataclass(frozen=True, slots=True)
class ScenarioMixturePopulation:
    profile: str
    seed: int
    count: int
    scenarios: tuple[GeneratedScenario, ...]
    family_counts: dict[str, int]
    fingerprint: str


class ScenarioMixtureBuilder:
    """Builds weighted synthetic populations for offline experiments only."""

    PROFILES = {
        "EQUAL_FAMILY": ScenarioMixtureProfile(
            name="EQUAL_FAMILY",
            weights={
                scenario_type: 1
                for scenario_type in ScenarioType
            },
        ),
        "LEGITIMATE_DOMINANT": ScenarioMixtureProfile(
            name="LEGITIMATE_DOMINANT",
            weights={
                ScenarioType.LEGITIMATE: 14,
                ScenarioType.LEGITIMATE_UNUSUAL: 3,
                ScenarioType.LEGITIMATE_NETWORK_HUB: 3,
                ScenarioType.ACCOUNT_TAKEOVER: 1,
                ScenarioType.IMPERSONATION: 1,
                ScenarioType.ADVANCE_FEE: 1,
                ScenarioType.MULE_RECIPIENT: 1,
                ScenarioType.RAPID_CASHOUT: 1,
            },
        ),
        "HARD_NEGATIVE_DOMINANT": ScenarioMixtureProfile(
            name="HARD_NEGATIVE_DOMINANT",
            weights={
                ScenarioType.LEGITIMATE: 4,
                ScenarioType.LEGITIMATE_UNUSUAL: 8,
                ScenarioType.LEGITIMATE_NETWORK_HUB: 8,
                ScenarioType.ACCOUNT_TAKEOVER: 1,
                ScenarioType.IMPERSONATION: 1,
                ScenarioType.ADVANCE_FEE: 1,
                ScenarioType.MULE_RECIPIENT: 1,
                ScenarioType.RAPID_CASHOUT: 1,
            },
        ),
        "SOCIAL_ENGINEERING_HEAVY": ScenarioMixtureProfile(
            name="SOCIAL_ENGINEERING_HEAVY",
            weights={
                ScenarioType.LEGITIMATE: 4,
                ScenarioType.LEGITIMATE_UNUSUAL: 2,
                ScenarioType.LEGITIMATE_NETWORK_HUB: 2,
                ScenarioType.ACCOUNT_TAKEOVER: 1,
                ScenarioType.IMPERSONATION: 5,
                ScenarioType.ADVANCE_FEE: 5,
                ScenarioType.MULE_RECIPIENT: 1,
                ScenarioType.RAPID_CASHOUT: 1,
            },
        ),
        "NETWORK_ABUSE_HEAVY": ScenarioMixtureProfile(
            name="NETWORK_ABUSE_HEAVY",
            weights={
                ScenarioType.LEGITIMATE: 4,
                ScenarioType.LEGITIMATE_UNUSUAL: 2,
                ScenarioType.LEGITIMATE_NETWORK_HUB: 2,
                ScenarioType.ACCOUNT_TAKEOVER: 1,
                ScenarioType.IMPERSONATION: 1,
                ScenarioType.ADVANCE_FEE: 1,
                ScenarioType.MULE_RECIPIENT: 5,
                ScenarioType.RAPID_CASHOUT: 5,
            },
        ),
    }

    def build(
        self,
        *,
        profile: str,
        count: int,
        seed: int,
        start_time: datetime | None = None,
    ) -> ScenarioMixturePopulation:
        selected = self.profile(profile)
        if count <= 0:
            raise ValueError(
                "Scenario count must be greater than zero."
            )

        start_time = start_time or datetime(
            2026,
            10,
            1,
            tzinfo=UTC,
        )
        scenario_types = self._allocate_types(
            selected.weights,
            count,
        )
        random.Random(seed).shuffle(scenario_types)
        generator = SyntheticScenarioGenerator(seed=seed)

        scenarios = tuple(
            generator._generate_scenario(  # noqa: SLF001
                index=index,
                scenario_type=scenario_type,
                occurred_at=(
                    start_time
                    + timedelta(minutes=index)
                ),
            )
            for index, scenario_type
            in enumerate(scenario_types)
        )
        family_counts = {
            scenario_type.value: scenario_types.count(
                scenario_type
            )
            for scenario_type in ScenarioType
        }

        return ScenarioMixturePopulation(
            profile=selected.name,
            seed=seed,
            count=count,
            scenarios=scenarios,
            family_counts=family_counts,
            fingerprint=self._fingerprint(scenarios),
        )

    @classmethod
    def profile(
        cls,
        name: str,
    ) -> ScenarioMixtureProfile:
        try:
            return cls.PROFILES[name]
        except KeyError as error:
            raise ValueError(
                f"Unknown scenario mixture profile: {name}."
            ) from error

    @staticmethod
    def _allocate_types(
        weights: dict[ScenarioType, int],
        count: int,
    ) -> list[ScenarioType]:
        total_weight = sum(weights.values())
        quotas = {
            scenario_type: count * weight / total_weight
            for scenario_type, weight in weights.items()
        }
        allocations = {
            scenario_type: int(quota)
            for scenario_type, quota in quotas.items()
        }
        remaining = count - sum(allocations.values())
        ranked = sorted(
            weights,
            key=lambda scenario_type: (
                -(quotas[scenario_type] - allocations[scenario_type]),
                list(weights).index(scenario_type),
            ),
        )
        for scenario_type in ranked[:remaining]:
            allocations[scenario_type] += 1

        return [
            scenario_type
            for scenario_type, allocation in allocations.items()
            for _ in range(allocation)
        ]

    @staticmethod
    def _fingerprint(
        scenarios: tuple[GeneratedScenario, ...],
    ) -> str:
        values = [
            {
                "transaction_id": scenario.transaction.transaction_id,
                "amount": str(scenario.transaction.amount),
                "scenario_type": scenario.scenario_type.value,
            }
            for scenario in scenarios
        ]
        return sha256(
            json.dumps(
                values,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
