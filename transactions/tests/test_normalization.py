from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.contracts import TransactionType
from transactions.models import Transaction
from transactions.services.normalization import (
    TransactionNormalizer,
)


class TransactionNormalizerTests(TestCase):
    def setUp(self):
        self.normalizer = TransactionNormalizer()

    def make_transaction(self, **overrides):
        data = {
            "transaction_id": "TX-DB-001",
            "sender_id": "CUS-001",
            "recipient_id": "CUS-002",
            "amount": Decimal("2500.00"),
            "transaction_type": Transaction.TransactionType.P2P,
            "occurred_at": timezone.now(),
        }

        data.update(overrides)

        return Transaction.objects.create(**data)

    def test_transaction_model_can_be_normalized(self):
        transaction = self.make_transaction()

        normalized = self.normalizer.normalize(transaction)

        self.assertEqual(
            normalized.transaction_id,
            "TX-DB-001",
        )

        self.assertEqual(
            normalized.sender_id,
            "CUS-001",
        )

        self.assertEqual(
            normalized.recipient_id,
            "CUS-002",
        )

        self.assertEqual(
            normalized.amount,
            Decimal("2500.00"),
        )

        self.assertEqual(
            normalized.transaction_type,
            TransactionType.P2P,
        )

    def test_normalizer_preserves_timestamp(self):
        occurred_at = timezone.now()

        transaction = self.make_transaction(
            occurred_at=occurred_at,
        )

        normalized = self.normalizer.normalize(transaction)

        self.assertEqual(
            normalized.occurred_at,
            occurred_at,
        )

    def test_missing_features_use_contract_defaults(self):
        transaction = self.make_transaction()

        normalized = self.normalizer.normalize(transaction)

        self.assertFalse(
            normalized.is_new_recipient
        )

        self.assertFalse(
            normalized.device_changed_recently
        )

        self.assertEqual(
            normalized.amount_vs_sender_mean,
            1.0,
        )

        self.assertEqual(
            normalized.recipient_pass_through_ratio,
            0.0,
        )