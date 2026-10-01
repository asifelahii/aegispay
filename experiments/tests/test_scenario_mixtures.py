from django.test import SimpleTestCase

from experiments.services.scenario_generator import (
    ScenarioType,
)
from experiments.services.scenario_mixtures import (
    ScenarioMixtureBuilder,
)


class ScenarioMixtureBuilderTests(SimpleTestCase):
    def setUp(self):
        self.builder = ScenarioMixtureBuilder()

    def test_exact_count_and_unique_transaction_ids(self):
        population = self.builder.build(
            profile="EQUAL_FAMILY",
            count=80,
            seed=42,
        )

        self.assertEqual(population.count, 80)
        self.assertEqual(len(population.scenarios), 80)
        self.assertEqual(
            len({
                scenario.transaction.transaction_id
                for scenario in population.scenarios
            }),
            80,
        )
        self.assertEqual(sum(population.family_counts.values()), 80)

    def test_same_seed_is_deterministic(self):
        first = self.builder.build(
            profile="SOCIAL_ENGINEERING_HEAVY",
            count=80,
            seed=42,
        )
        second = self.builder.build(
            profile="SOCIAL_ENGINEERING_HEAVY",
            count=80,
            seed=42,
        )

        self.assertEqual(first, second)

    def test_positive_weight_families_are_represented(self):
        population = self.builder.build(
            profile="LEGITIMATE_DOMINANT",
            count=600,
            seed=42,
        )

        self.assertTrue(
            all(
                population.family_counts[scenario_type.value] > 0
                for scenario_type in ScenarioType
            )
        )

    def test_unknown_profile_and_invalid_count_are_rejected(self):
        with self.assertRaises(ValueError):
            self.builder.profile("UNKNOWN")

        with self.assertRaises(ValueError):
            self.builder.build(
                profile="EQUAL_FAMILY",
                count=0,
                seed=42,
            )
