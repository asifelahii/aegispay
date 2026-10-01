from core.contracts import (
    DecisionReason,
    NormalizedTransaction,
    RiskAssessment,
    RiskBand,
)


class RulesRiskEngine:
    """
    Transparent deterministic baseline for transaction risk.

    The thresholds and weights are prototype assumptions.
    They are not claimed to represent production upay rules.

    This engine exists so AegisPay can:
    1. work end-to-end before ML training,
    2. provide an interpretable baseline,
    3. later compare ML performance against simple rules.
    """

    def assess(self, transaction: NormalizedTransaction) -> RiskAssessment:
        reasons: list[DecisionReason] = []

        self._check_new_recipient(transaction, reasons)
        self._check_recent_device_change(transaction, reasons)
        self._check_amount_deviation(transaction, reasons)
        self._check_sender_velocity(transaction, reasons)
        self._check_recipient_fan_in(transaction, reasons)
        self._check_pass_through(transaction, reasons)
        self._check_cashout_velocity(transaction, reasons)

        score = min(
            1.0,
            sum(reason.contribution for reason in reasons),
        )

        return RiskAssessment(
            score=round(score, 4),
            band=self._risk_band(score),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _check_new_recipient(
        transaction: NormalizedTransaction,
        reasons: list[DecisionReason],
    ) -> None:
        if transaction.is_new_recipient:
            reasons.append(
                DecisionReason(
                    code="NEW_RECIPIENT",
                    message="The recipient has not previously received money from this sender.",
                    contribution=0.15,
                )
            )

    @staticmethod
    def _check_recent_device_change(
        transaction: NormalizedTransaction,
        reasons: list[DecisionReason],
    ) -> None:
        if transaction.device_changed_recently:
            reasons.append(
                DecisionReason(
                    code="RECENT_DEVICE_CHANGE",
                    message="The sender recently changed devices.",
                    contribution=0.15,
                )
            )

    @staticmethod
    def _check_amount_deviation(
        transaction: NormalizedTransaction,
        reasons: list[DecisionReason],
    ) -> None:
        if transaction.amount_vs_sender_mean >= 3.0:
            reasons.append(
                DecisionReason(
                    code="VERY_HIGH_AMOUNT_DEVIATION",
                    message="The amount is at least three times the sender's usual amount.",
                    contribution=0.20,
                )
            )
        elif transaction.amount_vs_sender_mean >= 2.0:
            reasons.append(
                DecisionReason(
                    code="HIGH_AMOUNT_DEVIATION",
                    message="The amount is significantly above the sender's usual amount.",
                    contribution=0.10,
                )
            )

        if transaction.amount_vs_sender_p95 >= 1.25:
            reasons.append(
                DecisionReason(
                    code="ABOVE_SENDER_P95",
                    message="The amount is above the sender's historical high-value range.",
                    contribution=0.10,
                )
            )

    @staticmethod
    def _check_sender_velocity(
        transaction: NormalizedTransaction,
        reasons: list[DecisionReason],
    ) -> None:
        if transaction.sender_tx_count_10m >= 5:
            reasons.append(
                DecisionReason(
                    code="HIGH_SENDER_VELOCITY",
                    message="The sender has made an unusually high number of recent transactions.",
                    contribution=0.10,
                )
            )

    @staticmethod
    def _check_recipient_fan_in(
        transaction: NormalizedTransaction,
        reasons: list[DecisionReason],
    ) -> None:
        if (
            transaction.recipient_unique_senders_24h >= 10
            or transaction.recipient_fan_in_24h >= 15
        ):
            reasons.append(
                DecisionReason(
                    code="HIGH_RECIPIENT_FAN_IN",
                    message="The recipient is receiving funds from many sources.",
                    contribution=0.10,
                )
            )

    @staticmethod
    def _check_pass_through(
        transaction: NormalizedTransaction,
        reasons: list[DecisionReason],
    ) -> None:
        if transaction.recipient_pass_through_ratio >= 0.80:
            reasons.append(
                DecisionReason(
                    code="HIGH_PASS_THROUGH",
                    message="The recipient rapidly forwards a large share of incoming value.",
                    contribution=0.15,
                )
            )

    @staticmethod
    def _check_cashout_velocity(
        transaction: NormalizedTransaction,
        reasons: list[DecisionReason],
    ) -> None:
        if transaction.recipient_cashout_velocity_1h >= 0.70:
            reasons.append(
                DecisionReason(
                    code="RAPID_CASHOUT",
                    message="The recipient rapidly cashes out incoming funds.",
                    contribution=0.15,
                )
            )

    @staticmethod
    def _risk_band(score: float) -> RiskBand:
        if score >= 0.75:
            return RiskBand.CRITICAL

        if score >= 0.50:
            return RiskBand.HIGH

        if score >= 0.25:
            return RiskBand.MEDIUM

        return RiskBand.LOW