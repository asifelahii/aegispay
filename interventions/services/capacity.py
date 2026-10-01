from dataclasses import dataclass

from core.contracts import InterventionAction
from interventions.services.policy import (
    ActionEvaluation,
    PolicyDecision,
)


@dataclass(frozen=True, slots=True)
class ReviewCandidate:
    transaction_id: str
    policy: PolicyDecision


@dataclass(frozen=True, slots=True)
class ReviewAllocation:
    transaction_id: str
    original_action: InterventionAction
    final_action: InterventionAction
    review_value: float
    review_allocated: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ReviewCapacityResult:
    capacity: int
    requested_reviews: int
    allocated_reviews: int
    allocations: tuple[ReviewAllocation, ...]


class HumanReviewCapacityAllocator:
    """
    Allocates limited human-review capacity.

    Review candidates are prioritized by incremental expected value:

        best non-review expected cost
        - human-review expected cost

    Therefore review capacity is used where it provides the greatest
    modeled reduction in expected total harm.

    All costs and intervention-effectiveness values ultimately come
    from prototype policy assumptions. They are not measured upay
    production outcomes.
    """

    def allocate(
        self,
        candidates: list[ReviewCandidate],
        capacity: int,
    ) -> ReviewCapacityResult:
        if capacity < 0:
            raise ValueError(
                "Review capacity cannot be negative."
            )

        review_candidates = []

        allocations_by_id = {}

        for candidate in candidates:
            policy = candidate.policy

            if (
                policy.action
                != InterventionAction.HUMAN_REVIEW
            ):
                allocations_by_id[
                    candidate.transaction_id
                ] = ReviewAllocation(
                    transaction_id=(
                        candidate.transaction_id
                    ),
                    original_action=policy.action,
                    final_action=policy.action,
                    review_value=0.0,
                    review_allocated=False,
                    reason=(
                        "Human review was not selected by "
                        "the intervention policy."
                    ),
                )

                continue

            human_review = (
                self._evaluation_for_action(
                    policy,
                    InterventionAction.HUMAN_REVIEW,
                )
            )

            best_non_review = (
                self._best_non_review(
                    policy
                )
            )

            review_value = max(
                0.0,
                (
                    best_non_review.total_expected_cost
                    - human_review.total_expected_cost
                ),
            )

            review_candidates.append(
                (
                    review_value,
                    candidate.transaction_id,
                    policy,
                    best_non_review,
                )
            )

        review_candidates.sort(
            key=lambda item: (
                item[0],
                item[2].expected_fraud_exposure,
            ),
            reverse=True,
        )

        allocated_ids = {
            transaction_id
            for (
                review_value,
                transaction_id,
                policy,
                best_non_review,
            )
            in review_candidates[:capacity]
        }

        for (
            review_value,
            transaction_id,
            policy,
            best_non_review,
        ) in review_candidates:
            if transaction_id in allocated_ids:
                allocations_by_id[
                    transaction_id
                ] = ReviewAllocation(
                    transaction_id=transaction_id,
                    original_action=(
                        InterventionAction.HUMAN_REVIEW
                    ),
                    final_action=(
                        InterventionAction.HUMAN_REVIEW
                    ),
                    review_value=round(
                        review_value,
                        2,
                    ),
                    review_allocated=True,
                    reason=(
                        "Human review was allocated because "
                        "this transaction ranked within the "
                        "available review capacity by incremental "
                        "expected value."
                    ),
                )

            else:
                allocations_by_id[
                    transaction_id
                ] = ReviewAllocation(
                    transaction_id=transaction_id,
                    original_action=(
                        InterventionAction.HUMAN_REVIEW
                    ),
                    final_action=(
                        best_non_review.action
                    ),
                    review_value=round(
                        review_value,
                        2,
                    ),
                    review_allocated=False,
                    reason=(
                        "Human review was requested but capacity "
                        "was unavailable, so the best eligible "
                        "non-review intervention was selected."
                    ),
                )

        ordered_allocations = tuple(
            allocations_by_id[
                candidate.transaction_id
            ]
            for candidate in candidates
        )

        return ReviewCapacityResult(
            capacity=capacity,
            requested_reviews=len(
                review_candidates
            ),
            allocated_reviews=min(
                capacity,
                len(review_candidates),
            ),
            allocations=ordered_allocations,
        )

    @staticmethod
    def _evaluation_for_action(
        policy: PolicyDecision,
        action: InterventionAction,
    ) -> ActionEvaluation:
        for evaluation in policy.evaluations:
            if evaluation.action == action:
                return evaluation

        raise ValueError(
            f"{action.value} evaluation is unavailable."
        )

    @staticmethod
    def _best_non_review(
        policy: PolicyDecision,
    ) -> ActionEvaluation:
        alternatives = [
            evaluation
            for evaluation in policy.evaluations
            if evaluation.action
            != InterventionAction.HUMAN_REVIEW
        ]

        if not alternatives:
            raise ValueError(
                "At least one non-review intervention "
                "must be available."
            )

        return min(
            alternatives,
            key=lambda evaluation: (
                evaluation.total_expected_cost,
                evaluation.protection_rate,
            ),
        )