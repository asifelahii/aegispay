from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import networkx as nx
from django.db.models import Q, Sum
from django.utils import timezone

from core.contracts import NormalizedTransaction
from transactions.models import Transaction


class RecipientNetworkFeatureService:
    """
    Derives recipient/network features using only information that
    existed before the transaction being analyzed.

    These features are designed as prototype indicators of mule-like
    or rapid fund-movement behavior.

    They are not claimed to represent production upay fraud rules.
    """

    def enrich(
        self,
        transaction: Transaction,
        normalized: NormalizedTransaction,
    ) -> NormalizedTransaction:
        cutoff = transaction.occurred_at

        window_24h_start = cutoff - timezone.timedelta(hours=24)
        window_1h_start = cutoff - timezone.timedelta(hours=1)

        historical_24h = Transaction.objects.filter(
            occurred_at__gte=window_24h_start,
            occurred_at__lt=cutoff,
        )

        historical_1h = Transaction.objects.filter(
            occurred_at__gte=window_1h_start,
            occurred_at__lt=cutoff,
        )

        graph = self._build_graph(historical_24h)

        recipient_id = transaction.recipient_id

        unique_senders = self._unique_senders(
            historical_24h,
            recipient_id,
        )

        fan_in = self._fan_in(
            graph,
            recipient_id,
        )

        fan_out = self._fan_out(
            graph,
            recipient_id,
        )

        pass_through_ratio = self._pass_through_ratio(
            historical_24h,
            recipient_id,
        )

        cashout_velocity = self._cashout_velocity(
            historical_1h,
            recipient_id,
        )

        return replace(
            normalized,
            recipient_unique_senders_24h=unique_senders,
            recipient_fan_in_24h=fan_in,
            recipient_fan_out_24h=fan_out,
            recipient_pass_through_ratio=pass_through_ratio,
            recipient_cashout_velocity_1h=cashout_velocity,
        )

    @staticmethod
    def _build_graph(
        transactions,
    ) -> nx.DiGraph:
        graph = nx.DiGraph()

        for tx in transactions:
            sender = tx.sender_id
            recipient = tx.recipient_id

            if graph.has_edge(sender, recipient):
                graph[sender][recipient]["count"] += 1
                graph[sender][recipient]["amount"] += float(
                    tx.amount
                )
            else:
                graph.add_edge(
                    sender,
                    recipient,
                    count=1,
                    amount=float(tx.amount),
                )

        return graph

    @staticmethod
    def _unique_senders(
        transactions,
        recipient_id: str,
    ) -> int:
        return (
            transactions
            .filter(recipient_id=recipient_id)
            .values("sender_id")
            .distinct()
            .count()
        )

    @staticmethod
    def _fan_in(
        graph: nx.DiGraph,
        recipient_id: str,
    ) -> int:
        if recipient_id not in graph:
            return 0

        return int(
            graph.in_degree(
                recipient_id,
                weight="count",
            )
        )

    @staticmethod
    def _fan_out(
        graph: nx.DiGraph,
        recipient_id: str,
    ) -> int:
        if recipient_id not in graph:
            return 0

        return int(
            graph.out_degree(
                recipient_id,
                weight="count",
            )
        )

    @staticmethod
    def _pass_through_ratio(
        transactions,
        recipient_id: str,
    ) -> float:
        incoming = (
            transactions
            .filter(recipient_id=recipient_id)
            .aggregate(total=Sum("amount"))
            ["total"]
            or Decimal("0")
        )

        if incoming <= 0:
            return 0.0

        outgoing = (
            transactions
            .filter(sender_id=recipient_id)
            .aggregate(total=Sum("amount"))
            ["total"]
            or Decimal("0")
        )

        ratio = outgoing / incoming

        return round(
            min(float(ratio), 1.0),
            4,
        )

    @staticmethod
    def _cashout_velocity(
        transactions,
        recipient_id: str,
    ) -> float:
        incoming = (
            transactions
            .filter(recipient_id=recipient_id)
            .aggregate(total=Sum("amount"))
            ["total"]
            or Decimal("0")
        )

        if incoming <= 0:
            return 0.0

        cashout = (
            transactions
            .filter(
                sender_id=recipient_id,
                transaction_type=(
                    Transaction.TransactionType.CASH_OUT
                ),
            )
            .aggregate(total=Sum("amount"))
            ["total"]
            or Decimal("0")
        )

        ratio = cashout / incoming

        return round(
            min(float(ratio), 1.0),
            4,
        )