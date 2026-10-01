from datetime import UTC, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from core.contracts import (
    NormalizedTransaction,
    RiskBand,
    TransactionType,
)
from transactions.services.analysis import (
    TransactionAnalysisService,
)


class TransactionAnalysisServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = TransactionAnalysisService()

    def make_transaction(self, **overrides):
        data = {
            "transaction_id": "TX-000001",
            "sender_id": "CUS-001",
            "recipient_id": "CUS-002",
            "amount": Decimal("1500.00"),
            "transaction_type": TransactionType.P2P,
            "occurred_at": datetime.now(UTC),
        }

        data.update(overrides)

        return NormalizedTransaction(**data)

    def test_service_returns_analysis(self):
        transaction = self.make_transaction()

        analysis = self.service.analyze(transaction)

        self.assertEqual(
            analysis.transaction.transaction_id,
            "TX-000001",
        )

        self.assertEqual(
            analysis.risk.band,
            RiskBand.LOW,
        )

    def test_service_detects_high_risk_transaction(self):
        transaction = self.make_transaction(
            is_new_recipient=True,
            device_changed_recently=True,
            amount_vs_sender_mean=3.5,
            amount_vs_sender_p95=1.5,
        )

        analysis = self.service.analyze(transaction)

        self.assertEqual(
            analysis.risk.score,
            0.60,
        )

        self.assertEqual(
            analysis.risk.band,
            RiskBand.HIGH,
        )

    def test_service_preserves_reason_codes(self):
        transaction = self.make_transaction(
            is_new_recipient=True,
        )

        analysis = self.service.analyze(transaction)

        reason_codes = {
            reason.code
            for reason in analysis.risk.reasons
        }

        self.assertIn(
            "NEW_RECIPIENT",
            reason_codes,
        )