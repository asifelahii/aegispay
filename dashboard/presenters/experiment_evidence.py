import json
from functools import lru_cache
from pathlib import Path


SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "experiment_evidence.json"
)


@lru_cache(maxsize=1)
def load_evidence_snapshot():
    with SNAPSHOT_PATH.open(encoding="utf-8") as snapshot:
        return json.load(snapshot)


def _delta(candidate, legacy):
    return candidate - legacy


def present_experiment_evidence():
    snapshot = load_evidence_snapshot()
    reference = snapshot["reference"]
    legacy = reference["legacy"]
    canonical = reference["canonical"]
    reference_metrics = (
        {
            "label": "Probe rate",
            "legacy": f"{legacy['probe_rate']:.2%}",
            "canonical": f"{canonical['probe_rate']:.2%}",
            "delta": f"{_delta(canonical['probe_rate'], legacy['probe_rate']):+.2%}",
            "kind": "benefit",
        },
        {
            "label": "Synthetic prevention",
            "legacy": f"{legacy['prevention_rate']:.2%}",
            "canonical": f"{canonical['prevention_rate']:.2%}",
            "delta": f"{_delta(canonical['prevention_rate'], legacy['prevention_rate']):+.2%}",
            "kind": "benefit",
        },
        {
            "label": "Residual scam loss",
            "legacy": f"{legacy['residual_scam_loss']:,.2f}",
            "canonical": f"{canonical['residual_scam_loss']:,.2f}",
            "delta": f"{_delta(canonical['residual_scam_loss'], legacy['residual_scam_loss']):+,.2f}",
            "kind": "benefit",
        },
        {
            "label": "Legitimate total friction",
            "legacy": f"{legacy['legitimate_total_friction']:,.2f}",
            "canonical": f"{canonical['legitimate_total_friction']:,.2f}",
            "delta": f"{_delta(canonical['legitimate_total_friction'], legacy['legitimate_total_friction']):+,.2f}",
            "kind": "benefit",
        },
        {
            "label": "Review allocations",
            "legacy": str(legacy["allocated_reviews"]),
            "canonical": str(canonical["allocated_reviews"]),
            "delta": f"{_delta(canonical['allocated_reviews'], legacy['allocated_reviews']):+d}",
            "kind": "tradeoff",
        },
        {
            "label": "Modeled total cost",
            "legacy": f"{legacy['total_modeled_cost']:,.2f}",
            "canonical": f"{canonical['total_modeled_cost']:,.2f}",
            "delta": f"{_delta(canonical['total_modeled_cost'], legacy['total_modeled_cost']):+,.2f}",
            "kind": "benefit",
        },
    )
    chart = {
        "labels": [str(cost) for cost in snapshot["exp03a"]["probe_costs"]],
        "legacy": snapshot["exp03a"]["legacy_costs"],
        "canonical": snapshot["exp03a"]["canonical_costs"],
    }
    exp03a = snapshot["exp03a"]
    exp03a_rows = [
        {"probe_cost": cost, "legacy": legacy_cost, "canonical": canonical_cost}
        for cost, legacy_cost, canonical_cost in zip(
            exp03a["probe_costs"], exp03a["legacy_costs"], exp03a["canonical_costs"]
        )
    ]
    exp01 = snapshot["exp01"]
    matrix = [
        {
            "seed": seed,
            "cells": [
                {
                    "capacity": capacity,
                    "label": "Canonical directional advantage",
                }
                for capacity in exp01["capacities"]
            ],
        }
        for seed in exp01["seeds"]
    ]
    return {
        "snapshot_version": snapshot["snapshot_version"],
        "reference": reference,
        "reference_metrics": reference_metrics,
        "exp01": {**exp01, "matrix": matrix},
        "exp02": snapshot["exp02"],
        "exp03a": {**exp03a, "rows": exp03a_rows},
        "exp03b": snapshot["exp03b"],
        "chart": chart,
    }
