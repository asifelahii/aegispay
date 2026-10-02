from django.http import Http404
from django.shortcuts import render

from .presenters.transaction_detail import present_transaction_detail


def overview(request):
    """Render the Phase 1 analyst dashboard with synthetic demo data."""
    context = {
        "metrics": (
            {
                "label": "Transactions Analyzed",
                "value": "12,480",
                "supporting": "Across the prototype benchmark",
                "trend": "+8.4%",
                "trend_label": "vs. prior demo window",
                "icon": "activity",
                "tone": "blue",
            },
            {
                "label": "Flagged / Review Queue",
                "value": "42",
                "supporting": "14 allocated of 20 capacity",
                "trend": "70%",
                "trend_label": "review capacity in use",
                "icon": "shield-alert",
                "tone": "warning",
            },
            {
                "label": "Simulated Protected Value",
                "value": "$384K",
                "supporting": "Modeled synthetic benchmark value",
                "trend": "+12.6%",
                "trend_label": "vs. prior demo window",
                "icon": "spark",
                "tone": "cyan",
            },
            {
                "label": "Intervention Rate",
                "value": "18.6%",
                "supporting": "Across analyzed transactions",
                "trend": "Selective",
                "trend_label": "minimum-effective policy",
                "icon": "target",
                "tone": "violet",
            },
        ),
        "recent_transactions": (
            {
                "transaction_id": "TX-8420",
                "time": "10:42:18",
                "amount": "$1,240.00",
                "risk": "Low",
                "risk_tone": "low",
                "status": "Cleared",
                "status_tone": "success",
                "intervention": "Allowed",
            },
            {
                "time": "10:39:04",
                "amount": "$3,850.00",
                "risk": "Medium",
                "risk_tone": "medium",
                "status": "Monitored",
                "status_tone": "info",
                "intervention": "Contextual warning",
            },
            {
                "time": "10:34:51",
                "amount": "$8,420.00",
                "risk": "High",
                "risk_tone": "high",
                "status": "Protected",
                "status_tone": "warning",
                "intervention": "Verify",
            },
            {
                "transaction_id": "TX-12600",
                "time": "10:31:27",
                "amount": "$12,600.00",
                "risk": "Critical",
                "risk_tone": "critical",
                "status": "In review",
                "status_tone": "critical",
                "intervention": "Human review",
            },
            {
                "time": "10:26:09",
                "amount": "$6,780.00",
                "risk": "High",
                "risk_tone": "high",
                "status": "Cooling",
                "status_tone": "violet",
                "intervention": "Cooling period",
            },
        ),
        "risk_distribution": (
            {"label": "Low", "value": "61%", "count": "7,613", "tone": "low"},
            {"label": "Medium", "value": "23%", "count": "2,870", "tone": "medium"},
            {"label": "High", "value": "11%", "count": "1,373", "tone": "high"},
            {"label": "Critical", "value": "5%", "count": "624", "tone": "critical"},
        ),
        "interventions": (
            {"label": "Allow", "value": 61, "count": "7,613", "tone": "low"},
            {"label": "Contextual warning", "value": 16, "count": "1,997", "tone": "info"},
            {"label": "Scam warning", "value": 8, "count": "998", "tone": "warning"},
            {"label": "Verify", "value": 7, "count": "874", "tone": "high"},
            {"label": "Cooling period", "value": 5, "count": "624", "tone": "violet"},
            {"label": "Human review", "value": 3, "count": "374", "tone": "critical"},
        ),
        "review_capacity": {
            "allocated": 14,
            "capacity": 20,
            "remaining": 6,
            "percentage": 70,
        },
    }
    return render(request, "dashboard/overview.html", context)


def transaction_detail(request, transaction_id):
    detail = present_transaction_detail(transaction_id)
    if detail is None:
        raise Http404("Demo transaction was not found.")

    return render(
        request,
        "dashboard/transaction_detail.html",
        {"detail": detail},
    )
