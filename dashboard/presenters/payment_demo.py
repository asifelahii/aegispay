from dataclasses import replace
from decimal import Decimal

from core.contracts import ScamContext
from interventions.services.decision import (
    AegisPayDecision,
    AegisPayDecisionService,
)
from risk.services.rules import RulesRiskEngine

from .transaction_detail import get_demo_transaction


SCENARIO_TRANSACTION_IDS = {
    "normal": "TX-1240",
    "guided": "TX-8420",
    "strong": "TX-12600",
}


def get_payment_transaction(scenario):
    if scenario == "normal":
        return replace(
            get_demo_transaction("TX-8420").transaction,
            transaction_id="TX-1240",
            sender_id="CUS-DEMO",
            recipient_id="BEN-ALI",
            amount=Decimal("5000.00"),
            sender_account_age_days=730,
            is_new_recipient=False,
            device_changed_recently=False,
            sender_tx_count_10m=1,
            sender_tx_count_1h=2,
            amount_vs_sender_mean=1.1,
            amount_vs_sender_p95=0.8,
            recipient_account_age_days=420,
            recipient_unique_senders_24h=2,
            recipient_fan_in_24h=2,
            recipient_fan_out_24h=1,
            recipient_pass_through_ratio=0.05,
            recipient_cashout_velocity_1h=0.05,
        )
    transaction_id = SCENARIO_TRANSACTION_IDS.get(scenario)
    demo = get_demo_transaction(transaction_id) if transaction_id else None
    return demo.transaction if demo else None


def evaluate_payment(scenario, context=None):
    transaction = get_payment_transaction(scenario)
    if transaction is None:
        return None
    risk = RulesRiskEngine().assess(transaction)
    decision = AegisPayDecisionService().decide(
        transaction=transaction,
        base_risk=risk,
        context=context,
    )
    return transaction, decision


def present_customer_decision(
    decision: AegisPayDecision,
    scenario,
    recipient,
    amount,
    note,
    answer=None,
):
    action = decision.policy.action.value
    messages = {
        "ALLOW": (
            "Ready to continue",
            "No additional security check is required for this payment.",
            "Payment can continue.",
        ),
        "CONTEXTUAL_WARNING": (
            "Please double-check the recipient",
            "AegisPay recommends one quick check before you continue.",
            "Please double-check the recipient before continuing.",
        ),
        "SCAM_WARNING": (
            "Please review this payment carefully",
            "This payment has signs commonly associated with scam situations.",
            "Take a moment to confirm the recipient and purpose.",
        ),
        "VERIFY": (
            "Please verify before continuing",
            "Please verify the recipient and purpose before continuing.",
            "AegisPay recommends an additional verification step.",
        ),
        "COOLING_PERIOD": (
            "Payment paused for your protection",
            "For your protection, this payment should be paused briefly before continuing.",
            "This is prototype behavior; no timed production hold is active.",
        ),
        "HUMAN_REVIEW": (
            "Additional review recommended",
            "This payment requires additional review before it can continue.",
            "AegisPay recommends human review.",
        ),
    }
    heading, message, detail = messages[action]
    return {
        "scenario": scenario,
        "transaction_id": decision.transaction.transaction_id,
        "has_analyst_explanation": decision.transaction.transaction_id
        in {"TX-8420", "TX-12600"},
        "recipient": recipient,
        "amount": amount,
        "note": note,
        "answer": answer,
        "action": action,
        "heading": heading,
        "message": message,
        "detail": detail,
        "can_confirm": action in {"ALLOW", "CONTEXTUAL_WARNING"},
        "risk_band": decision.final_risk.band.value.title(),
        "question": decision.context_question,
    }


def context_for_answer(answer_key, answer):
    return ScamContext(**{answer_key: answer == "yes"})
