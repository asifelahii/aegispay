from dataclasses import dataclass

from core.contracts import (
    NormalizedTransaction,
    RiskAssessment,
)
from risk.services.rules import RulesRiskEngine


@dataclass(frozen=True, slots=True)
class TransactionAnalysis:
    transaction: NormalizedTransaction
    risk: RiskAssessment


class TransactionAnalysisService:
    """
    Application service responsible for analyzing transactions.

    Views and future APIs should call this service instead of calling
    a specific risk engine directly.

    This keeps the application independent from the current
    risk implementation.
    """

    def __init__(self, risk_engine=None):
        self.risk_engine = risk_engine or RulesRiskEngine()

    def analyze(
        self,
        transaction: NormalizedTransaction,
    ) -> TransactionAnalysis:
        risk = self.risk_engine.assess(transaction)

        return TransactionAnalysis(
            transaction=transaction,
            risk=risk,
        )