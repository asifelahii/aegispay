from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.contracts import (
    RiskBand,
    ScamContext,
)
from interventions.services.decision import (
    DecisionStatus,
)
from interventions.services.transaction_decision import (
    PersistedTransactionDecisionService,
)
from transactions.models import Transaction


class PersistedTransactionDecisionServiceTests(
    TestCase
):
    def setUp(self):
        self.service = (
            PersistedTransactionDecisionService()
        )

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

    def test_normal_persisted_transaction_can_be_allowed(self):
        current = self.create_transaction(
            transaction_id="TX-CURRENT",
            sender_id="CUS-001",
            recipient_id="CUS-002",
        )

        decision = self.service.decide(
            current
        )

        self.assertEqual(
            decision.status,
            DecisionStatus.DECIDED,
        )

        self.assertEqual(
            decision.final_risk.band,
            RiskBand.LOW,
        )

        self.assertIsNotNone(
            decision.policy
        )

    def test_suspicious_persisted_transaction_requests_context(
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
            amount="5000.00",
        )

        decision = self.service.decide(
            current
        )

        self.assertEqual(
            decision.status,
            DecisionStatus.NEEDS_CONTEXT,
        )

        self.assertIsNotNone(
            decision.context_question
        )

        self.assertEqual(
            decision.base_risk.score,
            0.45,
        )

        self.assertEqual(
            decision.base_risk.band,
            RiskBand.MEDIUM,
        )

    def test_context_answer_changes_full_pipeline_decision(
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

        decision = self.service.decide(
            current,
            context=ScamContext(
                phone_call=True,
            ),
        )

        self.assertEqual(
            decision.status,
            DecisionStatus.DECIDED,
        )

        self.assertEqual(
            decision.base_risk.score,
            0.45,
        )

        self.assertEqual(
            decision.final_risk.score,
            0.65,
        )

        self.assertEqual(
            decision.final_risk.band,
            RiskBand.HIGH,
        )

        self.assertIsNotNone(
            decision.policy
        )