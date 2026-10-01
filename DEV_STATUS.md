> TEMPORARY DEVELOPMENT CONTEXT.  
> Keep this file updated during implementation.  
> Delete it before final hackathon submission after durable information has been migrated into README/report documentation.

# AegisPay Development Status

## Repository State

- Branch: `main`
- HEAD: `12e10fc` (`feat(interventions): add decision-relevant context probe candidate`)
- Full Django test suite: **168 passing**
- Django system check: clean
- Migration check: no changes
- Current untracked development artifacts: `artifacts/` (six local JSON
  experiment outputs); do not commit without explicit instruction.
- No `.github/copilot-instructions.md` or `DEV_STATUS.md` existed before this
  task.

## Product

AegisPay is an Intent-Aware Adaptive Scam Intervention system for Mobile
Financial Services. It combines transaction behavior, beneficiary-network risk,
selective scam-context acquisition, minimum-effective intervention selection,
and constrained human-review capacity to ask what happened, why it is risky,
and what the service should do next.

The current research hypothesis is that selective context acquisition and
context-aware intervention selection may reduce simulated scam loss with less
legitimate-user friction at the same review capacity as a conventional
threshold policy. Current evidence does not prove the full hypothesis.

## Architecture

- Python with Django 6.1.1, SQLite for the MVP, and NetworkX 3.7.
- Django-first modular monolith: thin interfaces/views, application services,
  and typed dataclass/enum contracts.
- `transactions`: persistence, normalization, sender behavioral enrichment,
  and feature coordination.
- `network`: recipient/network feature enrichment using historical graph
  signals.
- `risk`: transparent deterministic rules baseline.
- `interventions`: Context Probe, context-risk adjustment, intervention policy,
  persisted transaction decisions, portfolio flow, and review-capacity
  allocation.
- `experiments`: synthetic scenario generation, baseline strategies, runner,
  comparison, diagnostics, friction accounting, Context Probe ablation/audit,
  and selectivity comparison.
- `core`: shared contracts including runtime transaction/risk types and
  evaluation-only `TransactionGroundTruth`.
- No UI work is started; README remains intentionally minimal and was not
  modified.

## Completed Capabilities

- Canonical transaction normalization and timezone-aware validation.
- Historical sender behavior features with a pre-transaction time boundary.
- Historical recipient/network features using NetworkX and pre-transaction
  windows.
- Transparent rules risk scoring with LOW, MEDIUM, HIGH, and CRITICAL bands.
- Selective legacy Context Probe with one targeted question for ambiguous risk.
- Context-risk adjustment and minimum-effective intervention policy.
- Limited human-review allocation by modeled incremental expected value.
- Portfolio decision flow that preserves input order and excludes pending
  context requests from review capacity.
- Deterministic synthetic scenarios and reproducible baseline comparisons.
- Separate accounting for intervention friction and Context Probe friction.
- Context Probe ablation, effectiveness audit, and decision-relevant selectivity
  candidate comparison.
- EXP-01 seed and review-capacity robustness validation infrastructure and
  reproducible management command.
- EXP-02 scenario-mixture sensitivity infrastructure and controlled stress-test
  results.

## Current Experiment State

The local artifacts are synthetic prototype simulations with `count=600`,
`seed=42`, `review_capacity=20`, and a round-robin scenario mixture. Ground
truth is recorded separately and used evaluation-only. The latest candidate
artifact has `candidate_status=experimental_not_promoted`.

## Latest Evidence

### Context Probe ablation

- No Context Probe: prevention **29.36%**, total modeled cost **773369.45**.
- Legacy AegisPay Context Probe: prevention **30.93%**, total modeled cost
  **761733.30**.
- Under these assumptions, the legacy probe adds measurable simulated value.

### Context Probe effectiveness audit

- 600 transactions; 525 probes; **87.50%** probe rate.
- 75 probes changed risk (**14.29%** of probes).
- 35 probes changed requested/effective action (**6.67%** of probes).
- Incremental prevented scam value: **16086.15**.
- Legitimate probe friction: **3750.00**.
- Net modeled cost savings: **11636.15**.
- Diagnostic conclusion: the concept appears useful under current assumptions,
  but the legacy question-selection policy is inefficient.

### Selectivity comparison

| Strategy | Probes | Probe rate | Prevention | Residual scam loss | Legitimate total friction | Allocated reviews | Total modeled cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| Legacy Context Probe | 525 | 87.50% | 30.93% | 705343.30 | 27990.00 | 3 | 761733.30 |
| Decision-Relevant candidate | 360 | 60.00% | 37.60% | 637291.80 | 26215.00 | 14 | 711376.80 |

These are one controlled synthetic configuration, not production results.

## EXP-01 Robustness Validation

- Tested seeds: `7, 21, 42, 84, 126`.
- Tested review capacities: `0, 5, 10, 20, 40`.
- Scenario count: `600` per controlled comparison.
- Controlled comparisons: **25** seed/capacity cells, with legacy and
  decision-relevant strategies evaluated on the same generated population.
- Standard deviations below are population standard deviations across the five
  seeds for each capacity.

| Capacity | Strategy | Mean probe rate | Probe-rate SD | Mean prevention | Prevention SD | Mean residual loss | Mean legitimate friction | Mean allocated reviews | Mean total modeled cost | Total-cost SD |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | Legacy | 87.50% | 0.0000 | 30.69% | 0.0013 | 719470.89 | 28146.00 | 0.00 | 773230.89 | 14159.4067 |
| 0 | Candidate | 58.70% | 0.0187 | 36.12% | 0.0010 | 663016.77 | 26351.00 | 0.00 | 724141.77 | 12733.6766 |
| 5 | Legacy | 87.50% | 0.0000 | 31.02% | 0.0018 | 716008.69 | 28146.00 | 2.00 | 771868.69 | 14099.1621 |
| 5 | Candidate | 58.70% | 0.0187 | 36.47% | 0.0010 | 659357.19 | 26351.00 | 5.00 | 724982.19 | 12766.6463 |
| 10 | Legacy | 87.50% | 0.0000 | 31.02% | 0.0018 | 716008.69 | 28146.00 | 2.00 | 771868.69 | 14099.1621 |
| 10 | Candidate | 58.70% | 0.0187 | 37.01% | 0.0008 | 653776.56 | 26351.00 | 9.60 | 723901.56 | 12171.4051 |
| 20 | Legacy | 87.50% | 0.0000 | 31.02% | 0.0018 | 716008.69 | 28146.00 | 2.00 | 771868.69 | 14099.1621 |
| 20 | Candidate | 58.70% | 0.0187 | 37.22% | 0.0019 | 651724.30 | 26351.00 | 10.80 | 723109.30 | 12671.7900 |
| 40 | Legacy | 87.50% | 0.0000 | 31.02% | 0.0018 | 716008.69 | 28146.00 | 2.00 | 771868.69 | 14099.1621 |
| 40 | Candidate | 58.70% | 0.0187 | 37.22% | 0.0019 | 651724.30 | 26351.00 | 10.80 | 723109.30 | 12671.7900 |

### EXP-01 Candidate-vs-legacy summary

All deltas use **candidate minus legacy**:

- Fewer-probe cells: **25/25**.
- Prevention better/equal/worse: **25/0/0**.
- Total modeled cost lower/equal/higher: **25/0/0**.
- Legitimate total friction lower: **25/25**.
- Prevention delta worst/best: **+0.0510 / +0.0667**.
- Total modeled cost delta worst/best: **-43789.50 / -52594.65**.

The candidate requested more reviews than legacy in the tested capacities:
mean allocated reviews were 5.00 versus 2.00 at capacity 5, 9.60 versus 2.00
at capacity 10, and 10.80 versus 2.00 at capacities 20 and 40. No allocation
exceeded its configured capacity, including capacity zero.

This is a synthetic prototype robustness experiment across random seeds and
review capacities. The deterministic round-robin scenario-family mixture means
seed changes primarily affect randomized transaction values, not scenario
prevalence. This is not scenario-mixture sensitivity, realistic prevalence
validation, production performance validation, or causal intervention evidence.
The candidate remains **experimental / not promoted**.

## EXP-02 Scenario-Mixture Sensitivity

The five profiles below are synthetic stress assumptions for controlled
benchmark construction. Their weights are not estimates of real upay fraud
prevalence or production transaction distributions.

| Profile | Weights by family |
|---|---|
| `EQUAL_FAMILY` | All eight families weight 1 |
| `LEGITIMATE_DOMINANT` | LEGITIMATE 14; LEGITIMATE_UNUSUAL 3; LEGITIMATE_NETWORK_HUB 3; each scam family 1 |
| `HARD_NEGATIVE_DOMINANT` | LEGITIMATE 4; LEGITIMATE_UNUSUAL 8; LEGITIMATE_NETWORK_HUB 8; each scam family 1 |
| `SOCIAL_ENGINEERING_HEAVY` | LEGITIMATE 4; LEGITIMATE_UNUSUAL 2; LEGITIMATE_NETWORK_HUB 2; ACCOUNT_TAKEOVER 1; IMPERSONATION 5; ADVANCE_FEE 5; MULE_RECIPIENT 1; RAPID_CASHOUT 1 |
| `NETWORK_ABUSE_HEAVY` | LEGITIMATE 4; LEGITIMATE_UNUSUAL 2; LEGITIMATE_NETWORK_HUB 2; ACCOUNT_TAKEOVER 1; IMPERSONATION 1; ADVANCE_FEE 1; MULE_RECIPIENT 5; RAPID_CASHOUT 5 |

- Seeds: `7, 21, 42, 84, 126`.
- Review capacities: `5, 20`.
- Scenario count: `600` per cell.
- Controlled cells: **50** profile/seed/capacity cells.
- Strategy-level runs: **100**.
- Population construction uses deterministic largest-remainder integer quotas.
- Each strategy in a cell uses the same scenario fingerprint and family counts.
- Standard deviations are population standard deviations across five seeds.

All deltas use **candidate minus legacy**. Negative probe-rate, residual-loss,
friction, or modeled-cost deltas favor lower candidate burden or harm; positive
prevention and review-allocation deltas mean higher candidate values.

### EXP-02 aggregate metrics

| Profile | Capacity | Strategy | Mean probe | Probe SD | Mean prevention | Prevention SD | Mean residual loss | Mean legitimate friction | Mean reviews | Mean total cost | Cost SD |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EQUAL_FAMILY | 5 | Legacy | 87.50% | 0.0000 | 30.64% | 0.0030 | 713520.35 | 28796.00 | 1.60 | 769458.35 | 15951.6506 |
| EQUAL_FAMILY | 5 | Candidate | 57.20% | 0.0177 | 36.48% | 0.0033 | 653497.47 | 26941.00 | 5.00 | 719718.47 | 15327.5363 |
| EQUAL_FAMILY | 20 | Legacy | 87.50% | 0.0000 | 30.64% | 0.0030 | 713520.35 | 28796.00 | 1.60 | 769458.35 | 15951.6506 |
| EQUAL_FAMILY | 20 | Candidate | 57.20% | 0.0177 | 36.97% | 0.0053 | 648424.40 | 26941.00 | 9.40 | 718905.40 | 15683.2020 |
| HARD_NEGATIVE_DOMINANT | 5 | Legacy | 84.00% | 0.0000 | 30.37% | 0.0052 | 228202.12 | 72944.00 | 0.20 | 321876.12 | 10012.2349 |
| HARD_NEGATIVE_DOMINANT | 5 | Candidate | 48.03% | 0.0188 | 36.27% | 0.0046 | 208888.06 | 68354.00 | 1.60 | 302222.06 | 9771.3679 |
| HARD_NEGATIVE_DOMINANT | 20 | Legacy | 84.00% | 0.0000 | 30.37% | 0.0052 | 228202.12 | 72944.00 | 0.20 | 321876.12 | 10012.2349 |
| HARD_NEGATIVE_DOMINANT | 20 | Candidate | 48.03% | 0.0188 | 36.27% | 0.0046 | 208888.06 | 68354.00 | 1.60 | 302222.06 | 9771.3679 |
| LEGITIMATE_DOMINANT | 5 | Legacy | 44.00% | 0.0000 | 30.37% | 0.0052 | 228202.12 | 27848.00 | 0.20 | 267996.12 | 9523.2260 |
| LEGITIMATE_DOMINANT | 5 | Candidate | 26.40% | 0.0110 | 36.27% | 0.0046 | 208888.06 | 26013.00 | 1.60 | 251097.06 | 9435.5896 |
| LEGITIMATE_DOMINANT | 20 | Legacy | 44.00% | 0.0000 | 30.37% | 0.0052 | 228202.12 | 27848.00 | 0.20 | 267996.12 | 9523.2260 |
| LEGITIMATE_DOMINANT | 20 | Candidate | 26.40% | 0.0110 | 36.27% | 0.0046 | 208888.06 | 26013.00 | 1.60 | 251097.06 | 9435.5896 |
| NETWORK_ABUSE_HEAVY | 5 | Legacy | 81.00% | 0.0000 | 30.18% | 0.0054 | 711516.65 | 21886.00 | 0.60 | 757360.65 | 18591.4876 |
| NETWORK_ABUSE_HEAVY | 5 | Candidate | 57.90% | 0.0127 | 38.32% | 0.0045 | 628513.38 | 20456.00 | 5.00 | 691743.38 | 15895.4856 |
| NETWORK_ABUSE_HEAVY | 20 | Legacy | 81.00% | 0.0000 | 30.18% | 0.0054 | 711516.65 | 21886.00 | 0.60 | 757360.65 | 18591.4876 |
| NETWORK_ABUSE_HEAVY | 20 | Candidate | 57.90% | 0.0127 | 39.29% | 0.0051 | 618582.28 | 20456.00 | 14.00 | 690482.28 | 15739.7457 |
| SOCIAL_ENGINEERING_HEAVY | 5 | Legacy | 81.00% | 0.0000 | 27.90% | 0.0050 | 734675.96 | 21886.00 | 0.60 | 778267.96 | 17743.1899 |
| SOCIAL_ENGINEERING_HEAVY | 5 | Candidate | 46.57% | 0.0270 | 32.53% | 0.0052 | 687505.69 | 20456.00 | 2.40 | 737057.69 | 16509.4158 |
| SOCIAL_ENGINEERING_HEAVY | 20 | Legacy | 81.00% | 0.0000 | 27.90% | 0.0050 | 734675.96 | 21886.00 | 0.60 | 778267.96 | 17743.1899 |
| SOCIAL_ENGINEERING_HEAVY | 20 | Candidate | 46.57% | 0.0270 | 32.53% | 0.0052 | 687505.69 | 20456.00 | 2.40 | 737057.69 | 16509.4158 |

### EXP-02 profile summaries

Each profile contains 10 cells: five seeds at each of two capacities.

| Profile | Fewer probes | Prevention better/equal/worse | Friction lower/equal/higher | Cost lower/equal/higher | Prevention delta min/max | Cost delta min/max | Mean review delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| EQUAL_FAMILY | 10/10 | 10/0/0 | 10/0/0 | 10/0/0 | +0.0558/+0.0682 | -55232.00/-47060.05 | +5.60 |
| HARD_NEGATIVE_DOMINANT | 10/10 | 10/0/0 | 10/0/0 | 10/0/0 | +0.0568/+0.0632 | -20539.20/-17706.85 | +1.40 |
| LEGITIMATE_DOMINANT | 10/10 | 10/0/0 | 10/0/0 | 10/0/0 | +0.0568/+0.0632 | -18064.30/-14781.85 | +1.40 |
| NETWORK_ABUSE_HEAVY | 10/10 | 10/0/0 | 10/0/0 | 10/0/0 | +0.0758/+0.0927 | -72816.50/-57725.25 | +8.90 |
| SOCIAL_ENGINEERING_HEAVY | 10/10 | 10/0/0 | 10/0/0 | 10/0/0 | +0.0441/+0.0486 | -43035.25/-38239.20 | +1.80 |

### EXP-02 global summary

- Candidate fewer probes: **50/50**.
- Prevention better/equal/worse: **50/0/0**.
- Legitimate friction lower/equal/higher: **50/0/0**.
- Modeled cost lower/equal/higher: **50/0/0**.
- Worst/best prevention delta: **+0.0441 / +0.0927**.
- Worst/best modeled-cost delta: **-14781.85 / -72816.50**.
- Largest positive review-allocation delta: **+16**.

The candidate remained **experimental / not promoted**. Review demand was
profile-sensitive, highest under `NETWORK_ABUSE_HEAVY`, where the mean review
allocation delta was `+8.90`. `HARD_NEGATIVE_DOMINANT` and
`LEGITIMATE_DOMINANT` had the lowest mean review delta at `+1.40`.

These are synthetic scenario-mixture stress tests. The configured profile
weights are experimental benchmark assumptions and are not estimates of real
upay fraud prevalence or production transaction distributions.

## Current Interpretation

The legacy Context Probe is not uniformly efficient: it frequently asks a
question without changing the requested action. The decision-relevant
candidate reduced probes and improved prevention, legitimate friction, and
modeled cost in every EXP-01 cell. This supports stability across the tested
seed and review-capacity grid under the current synthetic assumptions. EXP-02
also observed those directional differences in every tested synthetic mixture
stress cell, including hard-negative, legitimate-dominant, social-engineering,
and network-abuse-heavy profiles. Review demand increased for the candidate,
especially in the network-abuse-heavy profile. These observations do not
promote the candidate or establish production performance.

## Current Active Candidate

**Decision-Relevant Context Probe** is an experimental candidate implemented in
`interventions/services/selective_context_probe.py`. It uses only runtime
transaction/risk evidence and tests whether a hypothetical positive answer can
change the requested intervention. It does not use scenario type, hidden
synthetic context, or evaluation labels.

## Current Research Question

How sensitive are the observed candidate-versus-legacy differences to the
prototype Context Probe friction and intervention-cost assumptions?

## Locked Constraints

- Keep synthetic ground truth evaluation-only; never permit target leakage.
- Treat intervention and experiment values as prototype assumptions.
- Preserve human oversight and explainability; no autonomous permanent wallet
  freezing.
- Do not tune policies or assumptions only to outperform a baseline.
- Do not begin UI/UX work without explicit authorization.
- Follow the permanent rules in `.github/copilot-instructions.md`.

## Known Limitations

- The scenario generator is a synthetic scenario-coverage benchmark, not a
  realistic production prevalence estimate.
- Scenario prevalence must not be described as real-world upay prevalence.
- Intervention protection, friction, and operations values are prototype
  assumptions.
- The rules risk engine remains the transparent baseline; ML is not implemented.
- The candidate has been evaluated only on limited configurations.
- EXP-01 varies seeds and review capacity but not the scenario-family mixture;
  its round-robin mixture remains fixed.
- EXP-02 varies scenario-mixture weights but does not test friction-cost or
  intervention-cost sensitivity.
- No actual production upay data is integrated.
- No production causal intervention effects are measured.

## Next Planned Work

Run controlled Context Probe friction-cost and intervention-cost sensitivity
before any candidate promotion. Keep the same prevention, friction,
review-demand, and modeled-cost reporting used by EXP-01 and EXP-02.

## Future Backlog

- Scenario-mix/prevalence sensitivity.
- Logistic Regression baseline and XGBoost main model.
- Leakage-safe train/validation/test protocol and PR-AUC, precision, recall,
  F1, ROC-AUC, and calibration metrics where appropriate.
- SHAP and model-feature explanations; rule-versus-ML comparison.
- Justified public-data integration, potentially MoMTSim.
- UI/UX only after explicit authorization.
- Final README, architecture diagram, experiment tables/charts, limitations,
  Responsible AI, report, demo flow, and submission materials.

## Copilot Handoff

Before modifying code, read this file, `.github/copilot-instructions.md`, the
current README, the latest relevant tests, and the service/management command
for the requested area. Inspect current Git status and preserve the untracked
`artifacts/` directory. Do not promote the candidate automatically. The next
research task should address friction-cost and intervention-cost sensitivity,
keeping ground truth evaluation-only and reporting prevention, friction, review
demand, and modeled cost together.
