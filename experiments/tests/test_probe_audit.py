from datetime import UTC, datetime

from django.test import SimpleTestCase

from experiments.services.probe_audit import (
    ContextProbeAuditService,
)
from experiments.services.scenario_generator import (
    ScenarioType,
    SyntheticScenarioGenerator,
)


class ContextProbeAuditServiceTests(
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
            ContextProbeAuditService()
        )

    def audit(self):
        return self.service.audit(
            self.scenarios,
            review_capacity=5,
        )

    def test_all_transactions_are_audited(
        self,
    ):
        result = self.audit()

        self.assertEqual(
            result.summary.total_transactions,
            80,
        )

        self.assertEqual(
            len(result.rows),
            80,
        )

    def test_probe_rate_is_bounded(
        self,
    ):
        result = self.audit()

        self.assertGreater(
            result.summary.probe_rate,
            0,
        )

        self.assertLessEqual(
            result.summary.probe_rate,
            1,
        )

    def test_question_counts_equal_probe_count(
        self,
    ):
        result = self.audit()

        question_total = sum(
            item.count
            for item
            in result.question_counts
        )

        self.assertEqual(
            question_total,
            result.summary.total_probes,
        )

    def test_not_every_probe_changes_risk(
        self,
    ):
        result = self.audit()

        self.assertLess(
            result.summary.risk_changed_probes,
            result.summary.total_probes,
        )

    def test_not_every_probe_changes_requested_action(
        self,
    ):
        result = self.audit()

        self.assertLess(
            result.summary.requested_action_changed_probes,
            result.summary.total_probes,
        )

    def test_impersonation_has_risk_changing_probe(
        self,
    ):
        result = self.audit()

        row = next(
            item
            for item
            in result.by_scenario
            if item.scenario_type
            == ScenarioType.IMPERSONATION.value
        )

        self.assertGreater(
            row.risk_changes,
            0,
        )

    def test_legitimate_probe_friction_is_measured(
        self,
    ):
        result = self.audit()

        self.assertGreater(
            result.summary.legitimate_probe_friction,
            0,
        )

    def test_net_modeled_cost_savings_is_reported(
        self,
    ):
        result = self.audit()

        self.assertIsInstance(
            result.summary.net_modeled_cost_savings,
            float,
        )

    def test_negative_capacity_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            self.service.audit(
                self.scenarios,
                review_capacity=-1,
            )