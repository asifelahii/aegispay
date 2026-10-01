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

## Current Interpretation

The legacy Context Probe is not uniformly efficient: it frequently asks a
question without changing the requested action. The decision-relevant
candidate reduced probes and improved prevention, legitimate friction, and
modeled cost in every EXP-01 cell. This supports stability across the tested
seed and review-capacity grid under the current synthetic assumptions. It does
not establish robustness to scenario-mixture changes or production conditions,
and does not promote the candidate.

## Current Active Candidate

**Decision-Relevant Context Probe** is an experimental candidate implemented in
`interventions/services/selective_context_probe.py`. It uses only runtime
transaction/risk evidence and tests whether a hypothetical positive answer can
change the requested intervention. It does not use scenario type, hidden
synthetic context, or evaluation labels.

## Current Research Question

Does the candidate remain beneficial under controlled scenario-mixture
sensitivity, without relying on the deterministic round-robin mixture used by
the current synthetic generator?

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
- No actual production upay data is integrated.
- No production causal intervention effects are measured.

## Next Planned Work

Run controlled scenario-mixture sensitivity before any candidate promotion.
Keep the same prevention, friction, review-demand, and modeled-cost reporting
used by EXP-01. Further sensitivity work should separately test Context Probe
friction and intervention-cost assumptions.

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
research task should address controlled scenario-mixture sensitivity, keeping
ground truth evaluation-only and reporting prevention, friction, review demand,
and modeled cost together.
