# AegisPay Validation

## Interpretation Rule

All results below are **observed synthetic benchmark results** from controlled
prototype simulations. The interpretation following each result is bounded by
the synthetic population and modeled assumptions. These are not production
fraud, customer, analyst, or economic measurements.

## Reference Comparison

Configuration: 600 scenarios, seed 42, review capacity 20, matched population.

| Metric | Legacy Context Probe | Decision-Relevant Context Probe |
|---|---:|---:|
| Probe count | 525 | 360 |
| Probe rate | 87.50% | 60.00% |
| Simulated prevention | 30.93% | 37.60% |
| Residual scam loss | 705343.30 | 637291.80 |
| Legitimate total friction | 27990.00 | 26215.00 |
| Allocated reviews | 3 | 14 |
| Modeled total cost | 761733.30 | 711376.80 |

**Observed result:** the canonical probe asked 165 fewer questions, had higher
simulated prevention, lower modeled residual loss/friction/cost, and increased
allocated reviews from 3 to 14.

**Interpretation:** the selective candidate is promising under the locked
prototype assumptions, with higher review demand as a meaningful trade-off.

## Legacy Probe Audit

Observed synthetic audit: 600 transactions, 525 probes, 75 risk changes, and
35 requested/effective action changes. The audit indicated that the legacy
heuristic was useful under its assumptions but asked questions inefficiently.
This motivated the decision-relevance comparison; it does not establish
causal customer benefit.

## No-Probe Ablation

Observed synthetic reference: no Context Probe produced 29.36% simulated
prevention and 773369.45 modeled total cost. The legacy probe produced 30.93%
and 761733.30 respectively.

Interpretation: acquiring some context can add simulated value in this
benchmark. This does not prove that a probe is useful for every transaction.

## EXP-01 — Seed and Review Capacity Robustness

Observed design:

- seeds: `7, 21, 42, 84, 126`;
- capacities: `0, 5, 10, 20, 40`;
- 600 scenarios per matched comparison;
- 25 controlled cells.

Observed directional result: fewer probes, better prevention, lower modeled
cost, and lower legitimate friction in **25/25** cells. No review-capacity
violations occurred. Candidate review demand was higher at larger capacities,
averaging about 10.8 allocations at capacities 20 and 40.

Interpretation: the direction persisted across tested seeds and capacities,
but this is not prevalence, causal, or production validation.

## EXP-02 — Scenario-Mixture Sensitivity

Observed profiles:

1. EQUAL_FAMILY
2. LEGITIMATE_DOMINANT
3. HARD_NEGATIVE_DOMINANT
4. SOCIAL_ENGINEERING_HEAVY
5. NETWORK_ABUSE_HEAVY

The experiment contains **50 controlled cells**. The candidate had fewer
probes, better prevention, lower legitimate friction, and lower modeled cost
in **50/50** cells. Prevention deltas ranged approximately from +0.0441 to
+0.0927; modeled-cost deltas ranged approximately from -14781.85 to
-72816.50. The largest review-allocation increase was +16.

Interpretation: directional behavior was stable across these synthetic stress
mixtures. The weights are benchmark constructions, not real MFS prevalence.

## EXP-03A — Probe-Friction Sensitivity

Observed probe-cost assumptions: `0, 10, 25, 50, 100, 200`. The canonical
strategy's modeled total cost was lower at all six points. There was no
modeled-cost sign reversal.

Interpretation: within this accounting range, the comparison is not dependent
on one probe-cost point. Probe cost changes evaluation accounting here; it
does not change runtime decisions.

## EXP-03B — Intervention-Assumption Sensitivity

Observed design:

- 7 intervention-assumption profiles;
- 5 mixture profiles × 5 seeds × 2 capacities;
- 50 controlled cells per assumption profile;
- 350 controlled cells globally;
- 700 strategy runs globally.

Global observed directional summary:

| Outcome | Candidate result |
|---|---:|
| Fewer probes | 350/350 |
| Prevention better/equal/worse | 350/0/0 |
| Legitimate friction lower/equal/higher | 350/0/0 |
| Modeled cost lower/equal/higher | 350/0/0 |
| Review-capacity violations | 0 |

Interpretation: the directional result persisted across the tested intervention
assumptions. These are synthetic comparisons under assumed protection,
friction, operations, and review costs; they are not measured effectiveness.

## Promotion Decision

The canonical Decision-Relevant Context Probe was promoted to the default
prototype decision service after the controlled comparison and robustness
checks. The historical legacy service remains explicitly injectable for
baseline comparisons. This is a research/prototype decision, not a claim of
production readiness.

## Post-Promotion Reference Verification

The promoted default reproduced the canonical reference configuration:

- 600 scenarios;
- seed 42;
- review capacity 20;
- 360 probes / 60.00%;
- 37.60% simulated prevention;
- 637291.80 residual scam loss;
- 26215.00 legitimate friction;
- 14 allocated reviews;
- 711376.80 modeled total cost.

## Limitations

- Scenarios and weights are synthetic.
- No real upay or MFS transaction data is used.
- Intervention protection effectiveness is modeled.
- Friction, operations, and review costs are modeled.
- No customer behavior was observed.
- No production analyst workload study was performed.
- Ground truth is evaluation-only.
- No ML model is in the current validated pipeline.
- The evidence does not establish production fraud reduction or real savings.
