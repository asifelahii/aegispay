from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from core.contracts import (
    NormalizedTransaction,
    TransactionType,
)
from risk.services.rules import RulesRiskEngine


@dataclass(frozen=True, slots=True)
class NetworkEvent:
    time: str
    sender: str
    recipient: str
    transaction_type: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class NetworkScenario:
    key: str
    label: str
    focal_wallet: str
    events: tuple[NetworkEvent, ...]
    observation_window: str


SCENARIOS = {
    "concentrated": NetworkScenario(
        key="concentrated",
        label="Concentrated activity",
        focal_wallet="WLT-ALPHA",
        observation_window="Previous 24 hours; cash-out signal uses previous 1 hour",
        events=(
            NetworkEvent("09:10", "WLT-A01", "WLT-ALPHA", "P2P", Decimal("1200")),
            NetworkEvent("11:40", "WLT-A01", "WLT-ALPHA", "P2P", Decimal("800")),
            NetworkEvent("13:05", "WLT-A02", "WLT-ALPHA", "P2P", Decimal("1000")),
            NetworkEvent("15:20", "WLT-ALPHA", "WLT-B01", "P2P", Decimal("300")),
            NetworkEvent("16:15", "WLT-ALPHA", "WLT-CASH", "CASH_OUT", Decimal("150")),
        ),
    ),
    "high-risk": NetworkScenario(
        key="high-risk",
        label="High fan-in / pass-through activity",
        focal_wallet="WLT-FOCAL",
        observation_window="Previous 24 hours; cash-out signal uses previous 1 hour",
        events=(
            *(
                NetworkEvent(
                    f"{index + 8:02d}:10",
                    sender,
                    "WLT-FOCAL",
                    "P2P",
                    amount,
                )
                for sender, count, amount in (
                    ("WLT-S01", 4, Decimal("400")),
                    ("WLT-S02", 4, Decimal("450")),
                    ("WLT-S03", 3, Decimal("500")),
                    ("WLT-S04", 3, Decimal("550")),
                    ("WLT-S05", 3, Decimal("600")),
                    ("WLT-S06", 3, Decimal("650")),
                    ("WLT-S07", 2, Decimal("700")),
                    ("WLT-S08", 2, Decimal("750")),
                )
                for index in range(count)
            ),
            *(
                NetworkEvent(
                    f"{index + 10:02d}:45",
                    "WLT-FOCAL",
                    "WLT-DOWNSTREAM",
                    "P2P",
                    Decimal("352"),
                )
                for index in range(3)
            ),
            *(
                NetworkEvent(
                    f"{index + 11:02d}:20",
                    "WLT-FOCAL",
                    "WLT-CASH",
                    "CASH_OUT",
                    Decimal("1029.60"),
                )
                for index in range(10)
            ),
        ),
    ),
}


def _scenario_events(scenario: NetworkScenario) -> tuple[NetworkEvent, ...]:
    return scenario.events


def _metrics(scenario: NetworkScenario) -> dict:
    events = _scenario_events(scenario)
    inbound = [event for event in events if event.recipient == scenario.focal_wallet]
    outgoing = [event for event in events if event.sender == scenario.focal_wallet]
    incoming_amount = sum((event.amount for event in inbound), Decimal("0"))
    outgoing_amount = sum((event.amount for event in outgoing), Decimal("0"))
    cashout_amount = sum(
        (event.amount for event in outgoing if event.transaction_type == "CASH_OUT"),
        Decimal("0"),
    )
    return {
        "unique_senders": len({event.sender for event in inbound}),
        "fan_in": len(inbound),
        "fan_out": len(outgoing),
        "pass_through_ratio": min(
            float(outgoing_amount / incoming_amount)
            if incoming_amount
            else 0.0,
            1.0,
        ),
        "cashout_velocity": min(
            float(cashout_amount / incoming_amount)
            if incoming_amount
            else 0.0,
            1.0,
        ),
        "incoming_amount": incoming_amount,
        "outgoing_amount": outgoing_amount,
        "observed_value": incoming_amount + outgoing_amount,
    }


def _graph_payload(scenario: NetworkScenario) -> dict:
    events = _scenario_events(scenario)
    nodes = {scenario.focal_wallet: {
        "id": scenario.focal_wallet,
        "label": scenario.focal_wallet,
        "role": "Focal recipient",
        "kind": "focal",
        "x": 430,
        "y": 180,
    }}
    edges = {}
    for event in events:
        for wallet, role, kind, x, y in (
            (event.sender, "Sender", "sender", 90, 70),
            (event.recipient, "Recipient", "wallet", 700, 120),
        ):
            if wallet not in nodes:
                nodes[wallet] = {
                    "id": wallet,
                    "label": wallet,
                    "role": role,
                    "kind": (
                        "cashout"
                        if event.transaction_type == "CASH_OUT"
                        else kind
                    ),
                    "x": x,
                    "y": y + (len(nodes) % 5) * 55,
                }
        key = f"{event.sender}->{event.recipient}"
        if key not in edges:
            edges[key] = {
                "source": event.sender,
                "target": event.recipient,
                "count": 0,
                "amount": Decimal("0"),
                "risk_relevant": (
                    event.recipient == scenario.focal_wallet
                    or event.sender == scenario.focal_wallet
                ),
            }
        edges[key]["count"] += 1
        edges[key]["amount"] += event.amount

    return {
        "nodes": list(nodes.values()),
        "edges": [
            {
                **edge,
                "amount": f"{edge['amount']:.2f}",
                "width": min(6, 1 + edge["count"] * 0.35),
            }
            for edge in edges.values()
        ],
    }


def _risk_reasons(scenario: NetworkScenario, metrics: dict) -> tuple[str, ...]:
    transaction = NormalizedTransaction(
        transaction_id=f"NETWORK-{scenario.key}",
        sender_id="WLT-SYNTHETIC",
        recipient_id=scenario.focal_wallet,
        amount=Decimal("1000"),
        transaction_type=TransactionType.P2P,
        occurred_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
        recipient_unique_senders_24h=metrics["unique_senders"],
        recipient_fan_in_24h=metrics["fan_in"],
        recipient_fan_out_24h=metrics["fan_out"],
        recipient_pass_through_ratio=metrics["pass_through_ratio"],
        recipient_cashout_velocity_1h=metrics["cashout_velocity"],
    )
    return tuple(
        reason.code
        for reason in RulesRiskEngine().assess(transaction).reasons
        if reason.code
        in {"HIGH_RECIPIENT_FAN_IN", "HIGH_PASS_THROUGH", "RAPID_CASHOUT"}
    )


def present_network(scenario_key: str = "high-risk") -> dict:
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["high-risk"])
    metrics = _metrics(scenario)
    risk_reasons = _risk_reasons(scenario, metrics)
    return {
        "scenario": scenario,
        "scenario_options": tuple(
            (key, value.label) for key, value in SCENARIOS.items()
        ),
        "metrics": metrics,
        "risk_reasons": risk_reasons,
        "graph": _graph_payload(scenario),
        "events": _scenario_events(scenario),
        "network_concern": bool(risk_reasons),
        "summary": (
            "This recipient receives transactions from many wallets and moves "
            "a large share of incoming value onward. Recent cash-out activity "
            "also represents a substantial portion of the observed incoming value."
            if risk_reasons
            else "This synthetic example has a small connected set, modest movement, "
            "and limited cash-out activity, indicating lower network concern."
        ),
    }
