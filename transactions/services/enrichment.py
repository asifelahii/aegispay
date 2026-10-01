from core.contracts import NormalizedTransaction
from network.services.recipient_features import (
    RecipientNetworkFeatureService,
)
from transactions.models import Transaction
from transactions.services.features import (
    SenderBehaviorFeatureService,
)


class TransactionFeatureEnricher:
    """
    Coordinates all feature-enrichment services.

    Feature order is explicit and deterministic:
    1. sender behavioral features
    2. recipient/network features

    Future feature families can be added here without coupling
    Django views or risk engines to individual feature services.
    """

    def __init__(
        self,
        sender_features=None,
        recipient_features=None,
    ):
        self.sender_features = (
            sender_features
            or SenderBehaviorFeatureService()
        )

        self.recipient_features = (
            recipient_features
            or RecipientNetworkFeatureService()
        )

    def enrich(
        self,
        transaction: Transaction,
        normalized: NormalizedTransaction,
    ) -> NormalizedTransaction:
        enriched = self.sender_features.enrich(
            transaction,
            normalized,
        )

        enriched = self.recipient_features.enrich(
            transaction,
            enriched,
        )

        return enriched