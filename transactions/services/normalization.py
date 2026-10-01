from core.contracts import (
    NormalizedTransaction,
    TransactionType,
)
from transactions.models import Transaction


class TransactionNormalizer:
    """
    Converts persisted Django Transaction records into AegisPay's
    canonical NormalizedTransaction contract.

    Feature values that are not yet available from persistence are
    intentionally left at their contract defaults. Later feature
    engineering services will enrich them before risk inference.
    """

    def normalize(
        self,
        transaction: Transaction,
    ) -> NormalizedTransaction:
        return NormalizedTransaction(
            transaction_id=transaction.transaction_id,
            sender_id=transaction.sender_id,
            recipient_id=transaction.recipient_id,
            amount=transaction.amount,
            transaction_type=TransactionType(
                transaction.transaction_type
            ),
            occurred_at=transaction.occurred_at,
        )