from django.test import SimpleTestCase

from experiments.services.intervention_assumptions import (
    InterventionAssumptionBuilder,
)
from interventions.services.policy import MinimumEffectiveInterventionPolicy


class InterventionAssumptionTests(SimpleTestCase):
    def profiles(self, name):
        return InterventionAssumptionBuilder.build(name).profiles

    def test_baseline_matches_runtime_profiles(self):
        self.assertEqual(
            self.profiles("BASELINE"),
            MinimumEffectiveInterventionPolicy.PROFILES,
        )

    def test_protection_and_cost_transformations(self):
        lower = self.profiles("LOWER_PROTECTION")
        higher = self.profiles("HIGHER_PROTECTION")
        friction = self.profiles("HIGH_CUSTOMER_FRICTION")
        operations = self.profiles("HIGH_OPERATIONS_COST")
        review = self.profiles("HIGH_REVIEW_COST")

        self.assertEqual(lower[1].protection_rate, 0.12)
        self.assertEqual(higher[4].protection_rate, 0.84)
        self.assertEqual(higher[5].protection_rate, 0.95)
        self.assertEqual(friction[1].friction_cost, 240.0)
        self.assertEqual(operations[1].operations_cost, 60.0)
        self.assertEqual(review[5].operations_cost, 3600.0)

    def test_allow_and_all_profiles_are_valid(self):
        for assumption in InterventionAssumptionBuilder.all():
            for profile in assumption.profiles:
                self.assertGreaterEqual(profile.protection_rate, 0.0)
                self.assertLessEqual(profile.protection_rate, 1.0)
                self.assertGreaterEqual(profile.friction_cost, 0.0)
                self.assertGreaterEqual(profile.operations_cost, 0.0)
            self.assertEqual(assumption.profiles[0].protection_rate, 0.0)
            self.assertEqual(assumption.profiles[0].friction_cost, 0.0)
            self.assertEqual(assumption.profiles[0].operations_cost, 0.0)

    def test_conservative_stress_combines_transforms(self):
        profiles = self.profiles("CONSERVATIVE_STRESS")
        self.assertEqual(profiles[1].protection_rate, 0.12)
        self.assertEqual(profiles[1].friction_cost, 180.0)
        self.assertEqual(profiles[1].operations_cost, 60.0)
