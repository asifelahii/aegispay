from dataclasses import dataclass

from core.contracts import (
    InterventionAction,
    ScamContext,
)
from interventions.services.capacity import (
    HumanReviewCapacityAllocator,
    ReviewCandidate,
)
from interventions.services.decision import (
    AegisPayDecision,
    DecisionStatus,
)
from interventions.services.transaction_decision import (
    PersistedTransactionDecisionService,
)
from transactions.models import Transaction


@dataclass(frozen=True, slots=True)
class PortfolioTransactionRequest:
    transaction: Transaction
    context: ScamContext | None = None


@dataclass(frozen=True, slots=True)
class PortfolioTransactionDecision:
    transaction_id: str
    decision: AegisPayDecision
    effective_action: InterventionAction | None
    review_requested: bool
    review_allocated: bool
    review_value: float


@dataclass(frozen=True, slots=True)
class PortfolioDecisionResult:
    review_capacity: int
    total_transactions: int
    context_pending: int
    requested_reviews: int
    allocated_reviews: int
    decisions: tuple[
        PortfolioTransactionDecision,
        ...
    ]


class PortfolioDecisionService:
    """
    Coordinates transaction decisions across a portfolio while
    respecting limited human-review capacity.

    Transactions that still require customer context do not consume
    review capacity.

    Transactions with completed policy decisions are passed to the
    HumanReviewCapacityAllocator.

    The service preserves input ordering so experiment outputs and
    future UI/API consumers can reliably map results back to the
    original transactions.
    """

    def __init__(
        self,
        transaction_decision_service=None,
        capacity_allocator=None,
    ):
        self.transaction_decision_service = (
            transaction_decision_service
            or PersistedTransactionDecisionService()
        )

        self.capacity_allocator = (
            capacity_allocator
            or HumanReviewCapacityAllocator()
        )

    def decide(
        self,
        requests: list[
            PortfolioTransactionRequest
        ],
        *,
        review_capacity: int,
    ) -> PortfolioDecisionResult:
        self._validate_requests(
            requests
        )

        raw_decisions = []

        review_candidates = []

        for request in requests:
            decision = (
                self.transaction_decision_service.decide(
                    request.transaction,
                    context=request.context,
                )
            )

            transaction_id = (
                request.transaction.transaction_id
            )

            raw_decisions.append(
                (
                    transaction_id,
                    decision,
                )
            )

            if (
                decision.status
                == DecisionStatus.DECIDED
                and decision.policy is not None
            ):
                review_candidates.append(
                    ReviewCandidate(
                        transaction_id=transaction_id,
                        policy=decision.policy,
                    )
                )

        capacity_result = (
            self.capacity_allocator.allocate(
                review_candidates,
                capacity=review_capacity,
            )
        )

        allocation_by_id = {
            allocation.transaction_id: allocation
            for allocation
            in capacity_result.allocations
        }

        portfolio_decisions = []

        context_pending = 0

        for (
            transaction_id,
            decision,
        ) in raw_decisions:
            if (
                decision.status
                == DecisionStatus.NEEDS_CONTEXT
            ):
                context_pending += 1

                portfolio_decisions.append(
                    PortfolioTransactionDecision(
                        transaction_id=transaction_id,
                        decision=decision,
                        effective_action=None,
                        review_requested=False,
                        review_allocated=False,
                        review_value=0.0,
                    )
                )

                continue

            allocation = allocation_by_id[
                transaction_id
            ]

            review_requested = (
                allocation.original_action
                == InterventionAction.HUMAN_REVIEW
            )

            portfolio_decisions.append(
                PortfolioTransactionDecision(
                    transaction_id=transaction_id,
                    decision=decision,
                    effective_action=(
                        allocation.final_action
                    ),
                    review_requested=review_requested,
                    review_allocated=(
                        allocation.review_allocated
                    ),
                    review_value=(
                        allocation.review_value
                    ),
                )
            )

        return PortfolioDecisionResult(
            review_capacity=review_capacity,
            total_transactions=len(
                requests
            ),
            context_pending=context_pending,
            requested_reviews=(
                capacity_result.requested_reviews
            ),
            allocated_reviews=(
                capacity_result.allocated_reviews
            ),
            decisions=tuple(
                portfolio_decisions
            ),
        )

    @staticmethod
    def _validate_requests(
        requests: list[
            PortfolioTransactionRequest
        ],
    ) -> None:
        transaction_ids = [
            request.transaction.transaction_id
            for request in requests
        ]

        if (
            len(transaction_ids)
            != len(set(transaction_ids))
        ):
            raise ValueError(
                "Portfolio transaction IDs must be unique."
            )