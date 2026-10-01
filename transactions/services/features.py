from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from math import ceil

from django.db.models import QuerySet
from django.utils import timezone

from core.contracts import NormalizedTransaction
from transactions.models import Transaction


class SenderBehaviorFeatureService:
    """
    Enriches a NormalizedTransaction with sender behavioral features
    derived only from transaction history available before the
    transaction being analyzed.

    This strict time boundary is important to prevent future-data
    leakage during training, simulation, and evaluation.
    """

    def enrich(
        self,
        transaction: Transaction,
        normalized: NormalizedTransaction,
    ) -> NormalizedTransaction:
        history = self._sender_history(transaction)

        is_new_recipient = not history.filter(
            recipient_id=transaction.recipient_id
        ).exists()

        sender_tx_count_10m = history.filter(
            occurred_at__gte=(
                transaction.occurred_at
                - timezone.timedelta(minutes=10)
            )
        ).count()

        sender_tx_count_1h = history.filter(
            occurred_at__gte=(
                transaction.occurred_at
                - timezone.timedelta(hours=1)
            )
        ).count()

        historical_amounts = list(
            history.values_list("amount", flat=True)
        )

        amount_vs_sender_mean = self._amount_vs_mean(
            transaction.amount,
            historical_amounts,
        )

        amount_vs_sender_p95 = self._amount_vs_p95(
            transaction.amount,
            historical_amounts,
        )

        return replace(
            normalized,
            is_new_recipient=is_new_recipient,
            sender_tx_count_10m=sender_tx_count_10m,
            sender_tx_count_1h=sender_tx_count_1h,
            amount_vs_sender_mean=amount_vs_sender_mean,
            amount_vs_sender_p95=amount_vs_sender_p95,
        )

    @staticmethod
    def _sender_history(
        transaction: Transaction,
    ) -> QuerySet[Transaction]:
        return Transaction.objects.filter(
            sender_id=transaction.sender_id,
            occurred_at__lt=transaction.occurred_at,
        )

    @staticmethod
    def _amount_vs_mean(
        current_amount: Decimal,
        historical_amounts: list[Decimal],
    ) -> float:
        if not historical_amounts:
            return 1.0

        mean_amount = (
            sum(historical_amounts, Decimal("0"))
            / len(historical_amounts)
        )

        if mean_amount <= 0:
            return 1.0

        return round(
            float(current_amount / mean_amount),
            4,
        )

    @classmethod
    def _amount_vs_p95(
        cls,
        current_amount: Decimal,
        historical_amounts: list[Decimal],
    ) -> float:
        if not historical_amounts:
            return 1.0

        p95 = cls._nearest_rank_percentile(
            historical_amounts,
            0.95,
        )

        if p95 <= 0:
            return 1.0

        return round(
            float(current_amount / p95),
            4,
        )

    @staticmethod
    def _nearest_rank_percentile(
        values: list[Decimal],
        percentile: float,
    ) -> Decimal:
        if not values:
            raise ValueError(
                "At least one value is required."
            )

        ordered = sorted(values)

        rank = ceil(
            percentile * len(ordered)
        )

        index = max(
            0,
            rank - 1,
        )

        return ordered[index]