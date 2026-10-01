from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.contracts import TransactionType
from transactions.models import Transaction
from transactions.services.features import (
    SenderBehaviorFeatureService,
)
from transactions.services.normalization import (
    TransactionNormalizer,
)


class SenderBehaviorFeatureServiceTests(TestCase):
    def setUp(self):
        self.normalizer = TransactionNormalizer()
        self.features = SenderBehaviorFeatureService()

        self.now = timezone.now()

    def create_transaction(
        self,
        *,
        transaction_id,
        sender_id="CUS-001",
        recipient_id="CUS-002",
        amount="1000.00",
        occurred_at=None,
    ):
        return Transaction.objects.create(
            transaction_id=transaction_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            amount=Decimal(amount),
            transaction_type=TransactionType.P2P,
            occurred_at=occurred_at or self.now,
        )

    def enrich(self, transaction):
        normalized = self.normalizer.normalize(
            transaction
        )

        return self.features.enrich(
            transaction,
            normalized,
        )

    def test_first_transaction_treats_recipient_as_new(self):
        current = self.create_transaction(
            transaction_id="TX-001",
        )

        enriched = self.enrich(current)

        self.assertTrue(
            enriched.is_new_recipient
        )

    def test_previous_recipient_is_not_new(self):
        self.create_transaction(
            transaction_id="TX-HIST-001",
            recipient_id="CUS-002",
            occurred_at=(
                self.now
                - timedelta(days=1)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-002",
            recipient_id="CUS-002",
        )

        enriched = self.enrich(current)

        self.assertFalse(
            enriched.is_new_recipient
        )

    def test_transaction_velocity_uses_only_recent_history(self):
        self.create_transaction(
            transaction_id="TX-HIST-001",
            occurred_at=(
                self.now
                - timedelta(minutes=5)
            ),
        )

        self.create_transaction(
            transaction_id="TX-HIST-002",
            occurred_at=(
                self.now
                - timedelta(minutes=30)
            ),
        )

        self.create_transaction(
            transaction_id="TX-HIST-003",
            occurred_at=(
                self.now
                - timedelta(hours=2)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-003",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.sender_tx_count_10m,
            1,
        )

        self.assertEqual(
            enriched.sender_tx_count_1h,
            2,
        )

    def test_amount_vs_sender_mean_is_calculated(self):
        self.create_transaction(
            transaction_id="TX-HIST-001",
            amount="1000.00",
            occurred_at=(
                self.now
                - timedelta(days=2)
            ),
        )

        self.create_transaction(
            transaction_id="TX-HIST-002",
            amount="2000.00",
            occurred_at=(
                self.now
                - timedelta(days=1)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-004",
            amount="3000.00",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.amount_vs_sender_mean,
            2.0,
        )

    def test_amount_vs_p95_is_calculated(self):
        for index, amount in enumerate(
            [
                "100.00",
                "200.00",
                "300.00",
                "400.00",
                "500.00",
            ],
            start=1,
        ):
            self.create_transaction(
                transaction_id=f"TX-HIST-{index}",
                amount=amount,
                occurred_at=(
                    self.now
                    - timedelta(
                        days=10 - index
                    )
                ),
            )

        current = self.create_transaction(
            transaction_id="TX-005",
            amount="1000.00",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.amount_vs_sender_p95,
            2.0,
        )

    def test_future_transactions_are_never_used(self):
        self.create_transaction(
            transaction_id="TX-FUTURE",
            recipient_id="CUS-999",
            amount="999999.00",
            occurred_at=(
                self.now
                + timedelta(days=1)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-006",
            recipient_id="CUS-999",
            amount="1000.00",
        )

        enriched = self.enrich(current)

        self.assertTrue(
            enriched.is_new_recipient
        )

        self.assertEqual(
            enriched.sender_tx_count_1h,
            0,
        )

        self.assertEqual(
            enriched.amount_vs_sender_mean,
            1.0,
        )

    def test_current_transaction_is_not_its_own_history(self):
        current = self.create_transaction(
            transaction_id="TX-007",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.sender_tx_count_10m,
            0,
        )

        self.assertEqual(
            enriched.sender_tx_count_1h,
            0,
        )