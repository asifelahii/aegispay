from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
import random

from core.contracts import (
    NormalizedTransaction,
    ScamContext,
    TransactionGroundTruth,
    TransactionType,
)


class ScenarioType(StrEnum):
    LEGITIMATE = "LEGITIMATE"
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    IMPERSONATION = "IMPERSONATION"
    ADVANCE_FEE = "ADVANCE_FEE"
    MULE_RECIPIENT = "MULE_RECIPIENT"
    RAPID_CASHOUT = "RAPID_CASHOUT"


@dataclass(frozen=True, slots=True)
class GeneratedScenario:
    scenario_type: ScenarioType
    transaction: NormalizedTransaction
    context: ScamContext
    ground_truth: TransactionGroundTruth


class SyntheticScenarioGenerator:
    """
    Generates deterministic prototype scenarios for AegisPay
    experiments.

    Ground truth is stored separately from runtime transaction
    features so the risk engine cannot accidentally use the target
    label as evidence.

    These scenarios are synthetic assumptions for development and
    evaluation. They are not claimed to represent real upay fraud
    prevalence or production distributions.
    """

    def __init__(
        self,
        seed: int = 42,
    ):
        self.random = random.Random(seed)

    def generate(
        self,
        *,
        count: int,
        start_time: datetime | None = None,
    ) -> list[GeneratedScenario]:
        if count < 0:
            raise ValueError(
                "Scenario count cannot be negative."
            )

        start_time = (
            start_time
            or datetime.now(UTC)
        )

        scenarios = []

        scenario_types = list(
            ScenarioType
        )

        for index in range(count):
            scenario_type = (
                scenario_types[
                    index % len(scenario_types)
                ]
            )

            occurred_at = (
                start_time
                + timedelta(minutes=index)
            )

            scenarios.append(
                self._generate_scenario(
                    index=index,
                    scenario_type=scenario_type,
                    occurred_at=occurred_at,
                )
            )

        return scenarios

    def _generate_scenario(
        self,
        *,
        index: int,
        scenario_type: ScenarioType,
        occurred_at: datetime,
    ) -> GeneratedScenario:
        base_amount = Decimal(
            str(
                self.random.randint(
                    500,
                    5000,
                )
            )
        )

        transaction = NormalizedTransaction(
            transaction_id=f"SIM-{index + 1:06d}",
            sender_id=f"SENDER-{index + 1:05d}",
            recipient_id=f"RECIPIENT-{index + 1:05d}",
            amount=base_amount,
            transaction_type=TransactionType.P2P,
            occurred_at=occurred_at,
        )

        context = ScamContext()

        is_scam = (
            scenario_type
            != ScenarioType.LEGITIMATE
        )

        if (
            scenario_type
            == ScenarioType.ACCOUNT_TAKEOVER
        ):
            transaction = self._replace_transaction(
                transaction,
                device_changed_recently=True,
                is_new_recipient=True,
                amount_vs_sender_mean=3.8,
                amount_vs_sender_p95=1.6,
                sender_tx_count_10m=6,
            )

        elif (
            scenario_type
            == ScenarioType.IMPERSONATION
        ):
            transaction = self._replace_transaction(
                transaction,
                is_new_recipient=True,
                amount_vs_sender_mean=2.4,
            )

            context = ScamContext(
                phone_call=True,
                unknown_contact=True,
                urgency=True,
                support_impersonation=True,
            )

        elif (
            scenario_type
            == ScenarioType.ADVANCE_FEE
        ):
            transaction = self._replace_transaction(
                transaction,
                is_new_recipient=True,
                amount_vs_sender_mean=2.2,
                amount_vs_sender_p95=1.3,
            )

            context = ScamContext(
                unknown_contact=True,
                urgency=True,
                reward_or_prize=True,
            )

        elif (
            scenario_type
            == ScenarioType.MULE_RECIPIENT
        ):
            transaction = self._replace_transaction(
                transaction,
                is_new_recipient=True,
                recipient_unique_senders_24h=20,
                recipient_fan_in_24h=28,
                recipient_fan_out_24h=14,
                recipient_pass_through_ratio=0.90,
            )

        elif (
            scenario_type
            == ScenarioType.RAPID_CASHOUT
        ):
            transaction = self._replace_transaction(
                transaction,
                is_new_recipient=True,
                recipient_unique_senders_24h=12,
                recipient_fan_in_24h=18,
                recipient_pass_through_ratio=0.85,
                recipient_cashout_velocity_1h=0.90,
            )

            context = ScamContext(
                asked_to_keep_secret=True,
            )

        return GeneratedScenario(
            scenario_type=scenario_type,
            transaction=transaction,
            context=context,
            ground_truth=TransactionGroundTruth(
                is_scam=is_scam,
                scam_type=(
                    scenario_type.value
                    if is_scam
                    else None
                ),
            ),
        )

    @staticmethod
    def _replace_transaction(
        transaction: NormalizedTransaction,
        **changes,
    ) -> NormalizedTransaction:
        from dataclasses import replace

        return replace(
            transaction,
            **changes,
        )