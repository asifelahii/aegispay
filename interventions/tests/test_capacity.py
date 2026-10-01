from datetime import UTC, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from core.contracts import (
    InterventionAction,
    NormalizedTransaction,
    RiskAssessment,
    RiskBand,
    TransactionType,
)
from interventions.services.capacity import (
    HumanReviewCapacityAllocator,
    ReviewCandidate,
)
from interventions.services.policy import (
    MinimumEffectiveInterventionPolicy,
)


class HumanReviewCapacityAllocatorTests(
    SimpleTestCase
):
    def setUp(self):
        self.policy = (
            MinimumEffectiveInterventionPolicy()
        )

        self.allocator = (
            HumanReviewCapacityAllocator()
        )

    def make_transaction(
        self,
        *,
        transaction_id,
        amount,
    ):
        return NormalizedTransaction(
            transaction_id=transaction_id,
            sender_id="CUS-001",
            recipient_id="CUS-002",
            amount=Decimal(amount),
            transaction_type=TransactionType.P2P,
            occurred_at=datetime.now(UTC),
        )

    def make_risk(
        self,
        *,
        score,
        band,
    ):
        return RiskAssessment(
            score=score,
            band=band,
        )

    def make_candidate(
        self,
        *,
        transaction_id,
        amount,
        score,
        band,
    ):
        transaction = self.make_transaction(
            transaction_id=transaction_id,
            amount=amount,
        )

        policy = self.policy.select(
            transaction=transaction,
            risk=self.make_risk(
                score=score,
                band=band,
            ),
        )

        return ReviewCandidate(
            transaction_id=transaction_id,
            policy=policy,
        )

    def test_non_review_action_is_unchanged(self):
        candidate = self.make_candidate(
            transaction_id="TX-001",
            amount="1000.00",
            score=0.10,
            band=RiskBand.LOW,
        )

        result = self.allocator.allocate(
            [candidate],
            capacity=1,
        )

        allocation = result.allocations[0]

        self.assertEqual(
            allocation.original_action,
            InterventionAction.ALLOW,
        )

        self.assertEqual(
            allocation.final_action,
            InterventionAction.ALLOW,
        )

        self.assertFalse(
            allocation.review_allocated
        )

    def test_review_is_allocated_when_capacity_exists(self):
        candidate = self.make_candidate(
            transaction_id="TX-001",
            amount="5000.00",
            score=0.80,
            band=RiskBand.CRITICAL,
        )

        self.assertEqual(
            candidate.policy.action,
            InterventionAction.HUMAN_REVIEW,
        )

        result = self.allocator.allocate(
            [candidate],
            capacity=1,
        )

        allocation = result.allocations[0]

        self.assertTrue(
            allocation.review_allocated
        )

        self.assertEqual(
            allocation.final_action,
            InterventionAction.HUMAN_REVIEW,
        )

    def test_review_falls_back_when_capacity_is_zero(self):
        candidate = self.make_candidate(
            transaction_id="TX-001",
            amount="5000.00",
            score=0.80,
            band=RiskBand.CRITICAL,
        )

        result = self.allocator.allocate(
            [candidate],
            capacity=0,
        )

        allocation = result.allocations[0]

        self.assertFalse(
            allocation.review_allocated
        )

        self.assertNotEqual(
            allocation.final_action,
            InterventionAction.HUMAN_REVIEW,
        )

    def test_highest_review_value_gets_limited_slot(self):
        lower_value = self.make_candidate(
            transaction_id="TX-LOWER",
            amount="5000.00",
            score=0.80,
            band=RiskBand.CRITICAL,
        )

        higher_value = self.make_candidate(
            transaction_id="TX-HIGHER",
            amount="10000.00",
            score=0.80,
            band=RiskBand.CRITICAL,
        )

        self.assertEqual(
            lower_value.policy.action,
            InterventionAction.HUMAN_REVIEW,
        )

        self.assertEqual(
            higher_value.policy.action,
            InterventionAction.HUMAN_REVIEW,
        )

        result = self.allocator.allocate(
            [
                lower_value,
                higher_value,
            ],
            capacity=1,
        )

        allocations = {
            allocation.transaction_id: allocation
            for allocation in result.allocations
        }

        self.assertFalse(
            allocations[
                "TX-LOWER"
            ].review_allocated
        )

        self.assertTrue(
            allocations[
                "TX-HIGHER"
            ].review_allocated
        )

        self.assertGreater(
            allocations[
                "TX-HIGHER"
            ].review_value,
            allocations[
                "TX-LOWER"
            ].review_value,
        )

    def test_capacity_limit_is_respected(self):
        candidates = [
            self.make_candidate(
                transaction_id=f"TX-{index}",
                amount=str(
                    5000 + (index * 1000)
                ),
                score=0.80,
                band=RiskBand.CRITICAL,
            )
            for index in range(4)
        ]

        result = self.allocator.allocate(
            candidates,
            capacity=2,
        )

        allocated = [
            allocation
            for allocation in result.allocations
            if allocation.review_allocated
        ]

        self.assertEqual(
            len(allocated),
            2,
        )

        self.assertEqual(
            result.requested_reviews,
            4,
        )

        self.assertEqual(
            result.allocated_reviews,
            2,
        )

    def test_input_order_is_preserved_in_result(self):
        first = self.make_candidate(
            transaction_id="TX-FIRST",
            amount="5000.00",
            score=0.80,
            band=RiskBand.CRITICAL,
        )

        second = self.make_candidate(
            transaction_id="TX-SECOND",
            amount="10000.00",
            score=0.80,
            band=RiskBand.CRITICAL,
        )

        result = self.allocator.allocate(
            [first, second],
            capacity=1,
        )

        self.assertEqual(
            result.allocations[0].transaction_id,
            "TX-FIRST",
        )

        self.assertEqual(
            result.allocations[1].transaction_id,
            "TX-SECOND",
        )

    def test_negative_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.allocator.allocate(
                [],
                capacity=-1,
            )