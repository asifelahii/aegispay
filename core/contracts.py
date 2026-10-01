from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class TransactionType(StrEnum):
    P2P = "P2P"
    CASH_IN = "CASH_IN"
    CASH_OUT = "CASH_OUT"
    MERCHANT_PAYMENT = "MERCHANT_PAYMENT"
    BILL_PAYMENT = "BILL_PAYMENT"


class RiskBand(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InterventionAction(StrEnum):
    ALLOW = "ALLOW"
    CONTEXTUAL_WARNING = "CONTEXTUAL_WARNING"
    SCAM_WARNING = "SCAM_WARNING"
    VERIFY = "VERIFY"
    COOLING_PERIOD = "COOLING_PERIOD"
    HUMAN_REVIEW = "HUMAN_REVIEW"


@dataclass(frozen=True, slots=True)
class DecisionReason:
    code: str
    message: str
    contribution: float = 0.0

    def __post_init__(self):
        if not self.code.strip():
            raise ValueError("Decision reason code is required.")

        if not self.message.strip():
            raise ValueError("Decision reason message is required.")


@dataclass(frozen=True, slots=True)
class ScamContext:
    phone_call: bool | None = None
    unknown_contact: bool | None = None
    urgency: bool | None = None
    reward_or_prize: bool | None = None
    support_impersonation: bool | None = None
    asked_to_keep_secret: bool | None = None


@dataclass(frozen=True, slots=True)
class ContextQuestion:
    code: str
    prompt: str
    answer_key: str

    def __post_init__(self):
        if not self.code.strip():
            raise ValueError("Context question code is required.")

        if not self.prompt.strip():
            raise ValueError("Context question prompt is required.")

        if not self.answer_key.strip():
            raise ValueError("Context question answer key is required.")


@dataclass(frozen=True, slots=True)
class NormalizedTransaction:
    transaction_id: str
    sender_id: str
    recipient_id: str

    amount: Decimal
    transaction_type: TransactionType
    occurred_at: datetime

    # Sender/customer behavioral signals
    sender_account_age_days: int = 0
    is_new_recipient: bool = False
    device_changed_recently: bool = False

    sender_tx_count_10m: int = 0
    sender_tx_count_1h: int = 0

    amount_vs_sender_mean: float = 1.0
    amount_vs_sender_p95: float = 1.0

    # Recipient/network signals
    recipient_account_age_days: int = 0
    recipient_unique_senders_24h: int = 0
    recipient_fan_in_24h: int = 0
    recipient_fan_out_24h: int = 0
    recipient_pass_through_ratio: float = 0.0
    recipient_cashout_velocity_1h: float = 0.0

    def __post_init__(self):
        if not self.transaction_id.strip():
            raise ValueError("transaction_id is required.")

        if not self.sender_id.strip():
            raise ValueError("sender_id is required.")

        if not self.recipient_id.strip():
            raise ValueError("recipient_id is required.")

        if not isinstance(self.amount, Decimal):
            raise TypeError("amount must be a Decimal.")

        if self.amount <= Decimal("0"):
            raise ValueError("amount must be greater than zero.")

        if not isinstance(self.occurred_at, datetime):
            raise TypeError("occurred_at must be a datetime.")

        if (
            self.occurred_at.tzinfo is None
            or self.occurred_at.utcoffset() is None
        ):
            raise ValueError("occurred_at must be timezone-aware.")

        if self.sender_account_age_days < 0:
            raise ValueError("sender_account_age_days cannot be negative.")

        if self.recipient_account_age_days < 0:
            raise ValueError("recipient_account_age_days cannot be negative.")

        if not 0.0 <= self.recipient_pass_through_ratio <= 1.0:
            raise ValueError(
                "recipient_pass_through_ratio must be between 0 and 1."
            )


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    score: float
    band: RiskBand
    reasons: tuple[DecisionReason, ...] = ()

    def __post_init__(self):
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("Risk score must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class InterventionDecision:
    action: InterventionAction
    risk: RiskAssessment
    context_question: ContextQuestion | None = None


@dataclass(frozen=True, slots=True)
class TransactionGroundTruth:
    """
    Simulation/training metadata only.

    This object must never be passed into the runtime risk engine as
    transaction evidence.
    """

    is_scam: bool
    scam_type: str | None = None