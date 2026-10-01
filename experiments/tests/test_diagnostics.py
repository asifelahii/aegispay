from datetime import UTC, datetime

from django.test import SimpleTestCase

from experiments.services.diagnostics import (
    ExperimentDiagnosticsService,
)
from experiments.services.scenario_generator import (
    ScenarioType,
    SyntheticScenarioGenerator,
)


class ExperimentDiagnosticsServiceTests(
    SimpleTestCase
):
    def setUp(self):
        self.scenarios = (
            SyntheticScenarioGenerator(
                seed=42
            ).generate(
                count=80,
                start_time=datetime(
                    2026,
                    10,
                    1,
                    tzinfo=UTC,
                ),
            )
        )

        self.service = (
            ExperimentDiagnosticsService()
        )

    def analyze(self):
        return self.service.analyze(
            self.scenarios,
            review_capacity=5,
        )

    def find_row(
        self,
        result,
        *,
        strategy,
        scenario_type,
    ):
        for row in result.rows:
            if (
                row.strategy == strategy
                and row.scenario_type
                == scenario_type.value
            ):
                return row

        self.fail(
            "Expected diagnostic row "
            f"{strategy}/"
            f"{scenario_type.value}."
        )

    def test_all_four_strategies_are_present(self):
        result = self.analyze()

        strategies = {
            row.strategy
            for row in result.rows
        }

        self.assertEqual(
            strategies,
            {
                "NO_INTERVENTION",
                "HARD_THRESHOLD",
                "STATIC_TIER",
                "AEGISPAY",
            },
        )

    def test_hard_negative_families_are_included(self):
        result = self.analyze()

        scenario_types = {
            row.scenario_type
            for row in result.rows
        }

        self.assertIn(
            ScenarioType.LEGITIMATE_UNUSUAL.value,
            scenario_types,
        )

        self.assertIn(
            ScenarioType.LEGITIMATE_NETWORK_HUB.value,
            scenario_types,
        )

    def test_hard_negative_families_remain_legitimate(
        self,
    ):
        result = self.analyze()

        for scenario_type in (
            ScenarioType.LEGITIMATE_UNUSUAL,
            ScenarioType.LEGITIMATE_NETWORK_HUB,
        ):
            row = self.find_row(
                result,
                strategy="AEGISPAY",
                scenario_type=scenario_type,
            )

            self.assertEqual(
                row.scam_scenarios,
                0,
            )

            self.assertGreater(
                row.legitimate_scenarios,
                0,
            )

    def test_static_tier_creates_hard_negative_friction(
        self,
    ):
        result = self.analyze()

        unusual = self.find_row(
            result,
            strategy="STATIC_TIER",
            scenario_type=(
                ScenarioType.LEGITIMATE_UNUSUAL
            ),
        )

        network_hub = self.find_row(
            result,
            strategy="STATIC_TIER",
            scenario_type=(
                ScenarioType.LEGITIMATE_NETWORK_HUB
            ),
        )

        self.assertGreater(
            unusual.legitimate_friction_cost,
            0,
        )

        self.assertGreater(
            network_hub.legitimate_friction_cost,
            0,
        )

    def test_aegispay_probes_hard_negative_context(
        self,
    ):
        result = self.analyze()

        unusual = self.find_row(
            result,
            strategy="AEGISPAY",
            scenario_type=(
                ScenarioType.LEGITIMATE_UNUSUAL
            ),
        )

        network_hub = self.find_row(
            result,
            strategy="AEGISPAY",
            scenario_type=(
                ScenarioType.LEGITIMATE_NETWORK_HUB
            ),
        )

        self.assertGreater(
            unusual.context_probes,
            0,
        )

        self.assertGreater(
            network_hub.context_probes,
            0,
        )

    def test_negative_context_does_not_reduce_hard_negative_risk(
        self,
    ):
        result = self.analyze()

        for scenario_type in (
            ScenarioType.LEGITIMATE_UNUSUAL,
            ScenarioType.LEGITIMATE_NETWORK_HUB,
        ):
            row = self.find_row(
                result,
                strategy="AEGISPAY",
                scenario_type=scenario_type,
            )

            self.assertEqual(
                row.average_base_risk,
                row.average_final_risk,
            )

    def test_action_counts_equal_scenario_count(
        self,
    ):
        result = self.analyze()

        for row in result.rows:
            counted = sum(
                item.count
                for item
                in row.action_counts
            )

            self.assertEqual(
                counted,
                row.total_scenarios,
            )

    def test_negative_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.analyze(
                self.scenarios,
                review_capacity=-1,
            )