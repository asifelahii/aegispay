from core.contracts import ScamContext
from interventions.services.decision import (
    AegisPayDecision,
    AegisPayDecisionService,
)
from transactions.models import Transaction
from transactions.services.analysis import (
    TransactionAnalysisService,
)


class PersistedTransactionDecisionService:
    """
    Entry point for analyzing persisted Django transactions.

    Runtime pipeline:

    Transaction
        -> normalization
        -> feature enrichment
        -> base risk assessment
        -> context decision
        -> intervention decision
    """

    def __init__(
        self,
        analysis_service=None,
        decision_service=None,
    ):
        self.analysis_service = (
            analysis_service
            or TransactionAnalysisService()
        )

        self.decision_service = (
            decision_service
            or AegisPayDecisionService()
        )

    def decide(
        self,
        transaction: Transaction,
        context: ScamContext | None = None,
    ) -> AegisPayDecision:
        analysis = (
            self.analysis_service.analyze_persisted(
                transaction
            )
        )

        return self.decision_service.decide(
            transaction=analysis.transaction,
            base_risk=analysis.risk,
            context=context,
        )