from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.contracts import RiskBand
from transactions.models import Transaction
from transactions.services.analysis import (
    TransactionAnalysisService,
)


class TransactionIntelligencePipelineTests(TestCase):
    def setUp(self):
        self.service = TransactionAnalysisService()
        self.now = timezone.now()

    def create_transaction(
        self,
        *,
        transaction_id,
        sender_id,
        recipient_id,
        amount="1000.00",
        transaction_type=Transaction.TransactionType.P2P,
        occurred_at=None,
    ):
        return Transaction.objects.create(
            transaction_id=transaction_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            amount=Decimal(amount),
            transaction_type=transaction_type,
            occurred_at=occurred_at or self.now,
        )

    def test_persisted_transaction_runs_full_pipeline(self):
        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-001",
            recipient_id="WALLET-X",
            amount="1000.00",
        )

        analysis = self.service.analyze_persisted(
            current
        )

        self.assertEqual(
            analysis.transaction.transaction_id,
            "TX-CURRENT",
        )

        self.assertTrue(
            analysis.transaction.is_new_recipient
        )

        self.assertEqual(
            analysis.risk.score,
            0.15,
        )

        self.assertEqual(
            analysis.risk.band,
            RiskBand.LOW,
        )

    def test_sender_features_flow_into_risk_engine(self):
        self.create_transaction(
            transaction_id="TX-HIST-001",
            sender_id="CUS-001",
            recipient_id="CUS-OLD",
            amount="1000.00",
            occurred_at=(
                self.now
                - timedelta(days=1)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-001",
            recipient_id="WALLET-X",
            amount="4000.00",
        )

        analysis = self.service.analyze_persisted(
            current
        )

        self.assertTrue(
            analysis.transaction.is_new_recipient
        )

        self.assertEqual(
            analysis.transaction.amount_vs_sender_mean,
            4.0,
        )

        self.assertEqual(
            analysis.transaction.amount_vs_sender_p95,
            4.0,
        )

        reason_codes = {
            reason.code
            for reason in analysis.risk.reasons
        }

        self.assertIn(
            "NEW_RECIPIENT",
            reason_codes,
        )

        self.assertIn(
            "VERY_HIGH_AMOUNT_DEVIATION",
            reason_codes,
        )

        self.assertIn(
            "ABOVE_SENDER_P95",
            reason_codes,
        )

    def test_network_features_flow_into_risk_engine(self):
        for index in range(10):
            self.create_transaction(
                transaction_id=f"TX-IN-{index}",
                sender_id=f"CUS-{index}",
                recipient_id="WALLET-X",
                amount="500.00",
                occurred_at=(
                    self.now
                    - timedelta(hours=2)
                ),
            )

        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-999",
            recipient_id="WALLET-X",
            amount="1000.00",
        )

        analysis = self.service.analyze_persisted(
            current
        )

        self.assertEqual(
            analysis.transaction.recipient_unique_senders_24h,
            10,
        )

        self.assertEqual(
            analysis.transaction.recipient_fan_in_24h,
            10,
        )

        reason_codes = {
            reason.code
            for reason in analysis.risk.reasons
        }

        self.assertIn(
            "HIGH_RECIPIENT_FAN_IN",
            reason_codes,
        )

    def test_future_transactions_do_not_affect_pipeline(self):
        self.create_transaction(
            transaction_id="TX-FUTURE",
            sender_id="CUS-FUTURE",
            recipient_id="WALLET-X",
            amount="999999.00",
            occurred_at=(
                self.now
                + timedelta(days=1)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-001",
            recipient_id="WALLET-X",
            amount="1000.00",
        )

        analysis = self.service.analyze_persisted(
            current
        )

        self.assertEqual(
            analysis.transaction.recipient_unique_senders_24h,
            0,
        )

        self.assertEqual(
            analysis.transaction.recipient_fan_in_24h,
            0,
        )