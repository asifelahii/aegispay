from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.contracts import (
    InterventionAction,
    ScamContext,
)
from interventions.services.decision import (
    DecisionStatus,
)
from interventions.services.portfolio import (
    PortfolioDecisionService,
    PortfolioTransactionRequest,
)
from transactions.models import Transaction


class PortfolioDecisionServiceTests(
    TestCase
):
    def setUp(self):
        self.service = PortfolioDecisionService()
        self.now = timezone.now()

    def create_transaction(
        self,
        *,
        transaction_id,
        sender_id,
        recipient_id,
        amount="1000.00",
        occurred_at=None,
    ):
        return Transaction.objects.create(
            transaction_id=transaction_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            amount=Decimal(amount),
            transaction_type=(
                Transaction.TransactionType.P2P
            ),
            occurred_at=occurred_at or self.now,
        )

    def test_normal_transactions_keep_policy_actions(self):
        first = self.create_transaction(
            transaction_id="TX-001",
            sender_id="CUS-001",
            recipient_id="CUS-101",
            amount="500.00",
        )

        second = self.create_transaction(
            transaction_id="TX-002",
            sender_id="CUS-002",
            recipient_id="CUS-102",
            amount="700.00",
        )

        result = self.service.decide(
            [
                PortfolioTransactionRequest(
                    transaction=first
                ),
                PortfolioTransactionRequest(
                    transaction=second
                ),
            ],
            review_capacity=1,
        )

        self.assertEqual(
            result.total_transactions,
            2,
        )

        self.assertEqual(
            result.requested_reviews,
            0,
        )

        for decision in result.decisions:
            self.assertEqual(
                decision.effective_action,
                InterventionAction.ALLOW,
            )

    def test_context_pending_transaction_does_not_use_review_capacity(
        self,
    ):
        self.create_transaction(
            transaction_id="TX-HIST",
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
            recipient_id="CUS-NEW",
            amount="3000.00",
        )

        result = self.service.decide(
            [
                PortfolioTransactionRequest(
                    transaction=current
                )
            ],
            review_capacity=1,
        )

        item = result.decisions[0]

        self.assertEqual(
            item.decision.status,
            DecisionStatus.NEEDS_CONTEXT,
        )

        self.assertIsNone(
            item.effective_action
        )

        self.assertEqual(
            result.context_pending,
            1,
        )

        self.assertEqual(
            result.requested_reviews,
            0,
        )

    def test_completed_context_can_enter_intervention_policy(
        self,
    ):
        self.create_transaction(
            transaction_id="TX-HIST",
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
            recipient_id="CUS-NEW",
            amount="3000.00",
        )

        result = self.service.decide(
            [
                PortfolioTransactionRequest(
                    transaction=current,
                    context=ScamContext(
                        phone_call=True,
                    ),
                )
            ],
            review_capacity=1,
        )

        item = result.decisions[0]

        self.assertEqual(
            item.decision.status,
            DecisionStatus.DECIDED,
        )

        self.assertIsNotNone(
            item.effective_action
        )

        self.assertEqual(
            result.context_pending,
            0,
        )

    def test_review_capacity_is_shared_across_transactions(
        self,
    ):
        first = self.create_transaction(
            transaction_id="TX-HIGH-1",
            sender_id="CUS-A",
            recipient_id="WALLET-1",
            amount="10000.00",
        )

        second = self.create_transaction(
            transaction_id="TX-HIGH-2",
            sender_id="CUS-B",
            recipient_id="WALLET-2",
            amount="12000.00",
        )

        high_risk_context = ScamContext(
            phone_call=True,
            reward_or_prize=True,
            support_impersonation=True,
            asked_to_keep_secret=True,
        )

        result = self.service.decide(
            [
                PortfolioTransactionRequest(
                    transaction=first,
                    context=high_risk_context,
                ),
                PortfolioTransactionRequest(
                    transaction=second,
                    context=high_risk_context,
                ),
            ],
            review_capacity=1,
        )

        allocated = [
            item
            for item in result.decisions
            if item.review_allocated
        ]

        self.assertLessEqual(
            len(allocated),
            1,
        )

        self.assertLessEqual(
            result.allocated_reviews,
            1,
        )

    def test_zero_capacity_prevents_review_allocation(self):
        transaction = self.create_transaction(
            transaction_id="TX-HIGH",
            sender_id="CUS-A",
            recipient_id="WALLET-X",
            amount="10000.00",
        )

        result = self.service.decide(
            [
                PortfolioTransactionRequest(
                    transaction=transaction,
                    context=ScamContext(
                        phone_call=True,
                        reward_or_prize=True,
                        support_impersonation=True,
                        asked_to_keep_secret=True,
                    ),
                )
            ],
            review_capacity=0,
        )

        self.assertEqual(
            result.allocated_reviews,
            0,
        )

        self.assertFalse(
            result.decisions[
                0
            ].review_allocated
        )

    def test_result_preserves_input_order(self):
        first = self.create_transaction(
            transaction_id="TX-FIRST",
            sender_id="CUS-A",
            recipient_id="CUS-X",
        )

        second = self.create_transaction(
            transaction_id="TX-SECOND",
            sender_id="CUS-B",
            recipient_id="CUS-Y",
        )

        result = self.service.decide(
            [
                PortfolioTransactionRequest(
                    transaction=first
                ),
                PortfolioTransactionRequest(
                    transaction=second
                ),
            ],
            review_capacity=1,
        )

        self.assertEqual(
            result.decisions[
                0
            ].transaction_id,
            "TX-FIRST",
        )

        self.assertEqual(
            result.decisions[
                1
            ].transaction_id,
            "TX-SECOND",
        )

    def test_duplicate_transaction_ids_are_rejected(self):
        transaction = self.create_transaction(
            transaction_id="TX-001",
            sender_id="CUS-A",
            recipient_id="CUS-B",
        )

        request = PortfolioTransactionRequest(
            transaction=transaction
        )

        with self.assertRaises(ValueError):
            self.service.decide(
                [
                    request,
                    request,
                ],
                review_capacity=1,
            )