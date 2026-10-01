from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.contracts import TransactionType
from network.services.recipient_features import (
    RecipientNetworkFeatureService,
)
from transactions.models import Transaction
from transactions.services.normalization import (
    TransactionNormalizer,
)


class RecipientNetworkFeatureServiceTests(TestCase):
    def setUp(self):
        self.normalizer = TransactionNormalizer()
        self.features = RecipientNetworkFeatureService()
        self.now = timezone.now()

    def create_transaction(
        self,
        *,
        transaction_id,
        sender_id,
        recipient_id,
        amount="1000.00",
        transaction_type=TransactionType.P2P,
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

    def enrich(self, transaction):
        normalized = self.normalizer.normalize(
            transaction
        )

        return self.features.enrich(
            transaction,
            normalized,
        )

    def test_unique_senders_and_fan_in_are_calculated(self):
        for index in range(1, 4):
            self.create_transaction(
                transaction_id=f"TX-IN-{index}",
                sender_id=f"CUS-{index}",
                recipient_id="WALLET-X",
                occurred_at=(
                    self.now
                    - timedelta(hours=2)
                ),
            )

        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-999",
            recipient_id="WALLET-X",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.recipient_unique_senders_24h,
            3,
        )

        self.assertEqual(
            enriched.recipient_fan_in_24h,
            3,
        )

    def test_repeated_sender_increases_fan_in_but_not_unique_senders(self):
        self.create_transaction(
            transaction_id="TX-IN-1",
            sender_id="CUS-001",
            recipient_id="WALLET-X",
            occurred_at=(
                self.now
                - timedelta(hours=3)
            ),
        )

        self.create_transaction(
            transaction_id="TX-IN-2",
            sender_id="CUS-001",
            recipient_id="WALLET-X",
            occurred_at=(
                self.now
                - timedelta(hours=2)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-999",
            recipient_id="WALLET-X",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.recipient_unique_senders_24h,
            1,
        )

        self.assertEqual(
            enriched.recipient_fan_in_24h,
            2,
        )

    def test_fan_out_is_calculated(self):
        for index in range(1, 4):
            self.create_transaction(
                transaction_id=f"TX-OUT-{index}",
                sender_id="WALLET-X",
                recipient_id=f"CUS-{index}",
                occurred_at=(
                    self.now
                    - timedelta(hours=2)
                ),
            )

        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-999",
            recipient_id="WALLET-X",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.recipient_fan_out_24h,
            3,
        )

    def test_pass_through_ratio_is_calculated(self):
        self.create_transaction(
            transaction_id="TX-IN",
            sender_id="CUS-A",
            recipient_id="WALLET-X",
            amount="1000.00",
            occurred_at=(
                self.now
                - timedelta(hours=3)
            ),
        )

        self.create_transaction(
            transaction_id="TX-OUT",
            sender_id="WALLET-X",
            recipient_id="CUS-B",
            amount="800.00",
            occurred_at=(
                self.now
                - timedelta(hours=2)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-C",
            recipient_id="WALLET-X",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.recipient_pass_through_ratio,
            0.8,
        )

    def test_cashout_velocity_is_calculated(self):
        self.create_transaction(
            transaction_id="TX-IN",
            sender_id="CUS-A",
            recipient_id="WALLET-X",
            amount="1000.00",
            occurred_at=(
                self.now
                - timedelta(minutes=45)
            ),
        )

        self.create_transaction(
            transaction_id="TX-CASHOUT",
            sender_id="WALLET-X",
            recipient_id="AGENT-001",
            amount="700.00",
            transaction_type=TransactionType.CASH_OUT,
            occurred_at=(
                self.now
                - timedelta(minutes=20)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-C",
            recipient_id="WALLET-X",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.recipient_cashout_velocity_1h,
            0.7,
        )

    def test_transactions_older_than_24h_are_excluded(self):
        self.create_transaction(
            transaction_id="TX-OLD",
            sender_id="CUS-A",
            recipient_id="WALLET-X",
            occurred_at=(
                self.now
                - timedelta(hours=25)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-B",
            recipient_id="WALLET-X",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.recipient_unique_senders_24h,
            0,
        )

        self.assertEqual(
            enriched.recipient_fan_in_24h,
            0,
        )

    def test_future_transactions_are_excluded(self):
        self.create_transaction(
            transaction_id="TX-FUTURE",
            sender_id="CUS-A",
            recipient_id="WALLET-X",
            occurred_at=(
                self.now
                + timedelta(hours=1)
            ),
        )

        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-B",
            recipient_id="WALLET-X",
        )

        enriched = self.enrich(current)

        self.assertEqual(
            enriched.recipient_unique_senders_24h,
            0,
        )

        self.assertEqual(
            enriched.recipient_fan_in_24h,
            0,
        )