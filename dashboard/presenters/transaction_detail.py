from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from core.contracts import (
    NormalizedTransaction,
    ScamContext,
    TransactionType,
)
from interventions.services.context_risk import ContextRiskAdjuster
from interventions.services.decision import AegisPayDecisionService
from risk.services.rules import RulesRiskEngine


@dataclass(frozen=True, slots=True)
class DemoTransaction:
    transaction: NormalizedTransaction
    context: ScamContext | None
    answer: str | None
    scenario_label: str


def _demo_transactions() -> dict[str, DemoTransaction]:
    return {
        "TX-8420": DemoTransaction(
            transaction=NormalizedTransaction(
                transaction_id="TX-8420",
                sender_id="CUS-1048",
                recipient_id="BEN-7742",
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.P2P,
                occurred_at=datetime(
                    2026, 10, 2, 10, 34, 51, tzinfo=timezone.utc
                ),
                sender_account_age_days=418,
                is_new_recipient=True,
                device_changed_recently=True,
                sender_tx_count_10m=2,
                sender_tx_count_1h=4,
                amount_vs_sender_mean=2.5,
                amount_vs_sender_p95=1.6,
                recipient_account_age_days=31,
                recipient_unique_senders_24h=18,
                recipient_fan_in_24h=22,
                recipient_fan_out_24h=3,
                recipient_pass_through_ratio=0.62,
                recipient_cashout_velocity_1h=0.55,
            ),
            context=ScamContext(support_impersonation=True),
            answer="Yes — the person guiding the payment claimed to represent a financial institution.",
            scenario_label="Decision-relevant context probe",
        ),
        "TX-12600": DemoTransaction(
            transaction=NormalizedTransaction(
                transaction_id="TX-12600",
                sender_id="CUS-2081",
                recipient_id="BEN-8810",
                amount=Decimal("12600.00"),
                transaction_type=TransactionType.P2P,
                occurred_at=datetime(
                    2026, 10, 2, 10, 31, 27, tzinfo=timezone.utc
                ),
                sender_account_age_days=76,
                is_new_recipient=True,
                device_changed_recently=True,
                sender_tx_count_10m=7,
                sender_tx_count_1h=11,
                amount_vs_sender_mean=4.4,
                amount_vs_sender_p95=2.1,
                recipient_account_age_days=9,
                recipient_unique_senders_24h=32,
                recipient_fan_in_24h=41,
                recipient_fan_out_24h=12,
                recipient_pass_through_ratio=0.91,
                recipient_cashout_velocity_1h=0.88,
            ),
            context=None,
            answer=None,
            scenario_label="No probe required",
        ),
    }


def get_demo_transaction(transaction_id: str) -> DemoTransaction | None:
    return _demo_transactions().get(transaction_id)


def present_transaction_detail(transaction_id: str) -> dict | None:
    demo = get_demo_transaction(transaction_id)
    if demo is None:
        return None

    transaction = demo.transaction
    base_risk = RulesRiskEngine().assess(transaction)
    decision_service = AegisPayDecisionService()
    probe_result = decision_service.context_probe.evaluate(
        transaction=transaction,
        risk=base_risk,
    )
    decision_without_context = decision_service.decide(
        transaction=transaction,
        base_risk=base_risk,
    )
    decision = decision_without_context

    if demo.context is not None:
        decision = decision_service.decide(
            transaction=transaction,
            base_risk=base_risk,
            context=demo.context,
        )

    final_risk = decision.final_risk
    policy = decision.policy
    probe_question = probe_result.question
    context_changed = (
        demo.context is not None
        and (
            base_risk.score != final_risk.score
            or decision_without_context.policy is None
            or decision_without_context.policy.action != policy.action
        )
    )

    risk_factors = [
        {
            "code": reason.code,
            "message": reason.message,
            "contribution": f"+{reason.contribution:.2f}",
            "context": reason.code.startswith("CTX_"),
        }
        for reason in final_risk.reasons
    ]

    behavioral_metrics = (
        ("Amount vs sender mean", f"{transaction.amount_vs_sender_mean:.1f}×"),
        ("Amount vs sender p95", f"{transaction.amount_vs_sender_p95:.1f}×"),
        ("Sender transactions / 10m", str(transaction.sender_tx_count_10m)),
        ("Sender transactions / 1h", str(transaction.sender_tx_count_1h)),
        ("New recipient", "Yes" if transaction.is_new_recipient else "No"),
        (
            "Device changed recently",
            "Yes" if transaction.device_changed_recently else "No",
        ),
    )
    network_metrics = (
        ("Unique senders / 24h", str(transaction.recipient_unique_senders_24h)),
        ("Fan-in / 24h", str(transaction.recipient_fan_in_24h)),
        ("Fan-out / 24h", str(transaction.recipient_fan_out_24h)),
        (
            "Pass-through ratio",
            f"{transaction.recipient_pass_through_ratio:.0%}",
        ),
        (
            "Cash-out velocity / 1h",
            f"{transaction.recipient_cashout_velocity_1h:.0%}",
        ),
    )

    selected_evaluation = next(
        evaluation
        for evaluation in policy.evaluations
        if evaluation.action == policy.action
    )

    return {
        "transaction_id": transaction.transaction_id,
        "scenario_label": demo.scenario_label,
        "transaction": transaction,
        "transaction_type_label": transaction.transaction_type.value.replace(
            "_", " "
        ).title(),
        "occurred_at_label": transaction.occurred_at.strftime(
            "%d %b %Y, %H:%M UTC"
        ),
        "base_risk": base_risk,
        "final_risk": final_risk,
        "risk_band_label": final_risk.band.value.title(),
        "risk_score_label": f"{final_risk.score:.2f}",
        "risk_factors": risk_factors,
        "behavioral_metrics": behavioral_metrics,
        "network_metrics": network_metrics,
        "network_reason_fired": any(
            reason["code"]
            in {"HIGH_RECIPIENT_FAN_IN", "HIGH_PASS_THROUGH", "RAPID_CASHOUT"}
            for reason in risk_factors
        ),
        "probe": {
            "asked": probe_question is not None,
            "question": probe_question.prompt if probe_question else None,
            "answer": demo.answer,
            "reason": probe_result.reason,
            "before_score": f"{base_risk.score:.2f}",
            "after_score": f"{final_risk.score:.2f}",
            "before_action": (
                decision_without_context.policy.action.value
                if decision_without_context.policy
                else "Context required"
            ),
            "after_action": policy.action.value,
            "changed": context_changed,
        },
        "intervention": {
            "action": policy.action.value.replace("_", " "),
            "action_code": policy.action.value,
            "reason": policy.reason,
            "protection_rate": f"{selected_evaluation.protection_rate:.0%}",
            "friction_cost": f"${selected_evaluation.friction_cost:,.2f}",
            "operations_cost": f"${selected_evaluation.operations_cost:,.2f}",
            "residual_loss": f"${selected_evaluation.expected_residual_loss:,.2f}",
            "total_cost": f"${selected_evaluation.total_expected_cost:,.2f}",
            "review_requested": policy.action.value == "HUMAN_REVIEW",
        },
        "review": {
            "involved": policy.action.value == "HUMAN_REVIEW",
            "note": (
                "Allocation is determined at portfolio level; this prototype detail view does not claim an allocation."
            ),
        },
    }
