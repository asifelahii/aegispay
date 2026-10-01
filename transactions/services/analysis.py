from dataclasses import dataclass

from core.contracts import (
    NormalizedTransaction,
    RiskAssessment,
)
from risk.services.rules import RulesRiskEngine
from transactions.models import Transaction
from transactions.services.enrichment import (
    TransactionFeatureEnricher,
)
from transactions.services.normalization import (
    TransactionNormalizer,
)


@dataclass(frozen=True, slots=True)
class TransactionAnalysis:
    transaction: NormalizedTransaction
    risk: RiskAssessment


class TransactionAnalysisService:
    """
    Main application-level transaction analysis service.

    Runtime flow:

    persisted Transaction
        -> normalization
        -> feature enrichment
        -> risk engine
        -> TransactionAnalysis

    The existing analyze() method remains available for already
    normalized transactions such as simulations and experiments.
    """

    def __init__(
        self,
        risk_engine=None,
        normalizer=None,
        feature_enricher=None,
    ):
        self.risk_engine = (
            risk_engine
            or RulesRiskEngine()
        )

        self.normalizer = (
            normalizer
            or TransactionNormalizer()
        )

        self.feature_enricher = (
            feature_enricher
            or TransactionFeatureEnricher()
        )

    def analyze(
        self,
        transaction: NormalizedTransaction,
    ) -> TransactionAnalysis:
        risk = self.risk_engine.assess(
            transaction
        )

        return TransactionAnalysis(
            transaction=transaction,
            risk=risk,
        )

    def analyze_persisted(
        self,
        transaction: Transaction,
    ) -> TransactionAnalysis:
        normalized = self.normalizer.normalize(
            transaction
        )

        enriched = self.feature_enricher.enrich(
            transaction,
            normalized,
        )

        return self.analyze(
            enriched
        )