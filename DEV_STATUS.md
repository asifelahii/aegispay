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
truth is recorded separately and used evaluation-only. The latest sensitivity
artifact records the pre-promotion experiment with
`candidate_status=experimental_not_promoted`; runtime promotion is captured
separately below.

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
At that stage, the candidate remained **experimental / not promoted**.

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

At that stage, the candidate remained **experimental / not promoted**. Review demand was
profile-sensitive, highest under `NETWORK_ABUSE_HEAVY`, where the mean review
allocation delta was `+8.90`. `HARD_NEGATIVE_DOMINANT` and
`LEGITIMATE_DOMINANT` had the lowest mean review delta at `+1.40`.

These are synthetic scenario-mixture stress tests. The configured profile
weights are experimental benchmark assumptions and are not estimates of real
upay fraud prevalence or production transaction distributions.

## EXP-03A Context Probe Friction-Cost Sensitivity

EXP-03A isolates the Context Probe friction-cost accounting assumption. Probe
cost is not a runtime input to risk scoring, Context Probe selection,
intervention selection, or review allocation.

- Profiles: `EQUAL_FAMILY`, `LEGITIMATE_DOMINANT`,
  `HARD_NEGATIVE_DOMINANT`, `SOCIAL_ENGINEERING_HEAVY`,
  `NETWORK_ABUSE_HEAVY`.
- Seeds: `7, 21, 42, 84, 126`.
- Review capacities: `5, 20`.
- Count: `600` per base cell.
- Probe-cost assumptions: `0, 10, 25, 50, 100, 200`.
- Base runtime cells: **50**.
- Runtime executions: **100** strategy-level executions.
- Assumption-evaluation cells: **300**.
- Evaluated metric rows: **600**.
- Runtime outcomes were reused; only friction accounting and total modeled
  cost were recomputed per probe-cost assumption.
- All values are modeled prototype sensitivity assumptions, not measured
  customer-friction estimates or production economics.

All deltas use **candidate minus legacy**. Negative friction or modeled-cost
deltas favor the candidate; positive prevention or review deltas mean higher
candidate values.

### EXP-03A invariance validation

Across every fixed profile, seed, capacity, and strategy, changing probe cost
left the following unchanged: context probes, probe rate, prevention rate,
prevented scam value, residual scam loss, requested reviews, allocated reviews,
operations cost, and legitimate intervention friction. The experiment reported
no invariant violations.

### EXP-03A global aggregates by probe cost

| Probe cost | Strategy | Mean intervention friction | Mean probe friction | Mean total friction | Mean total modeled cost | Total-cost SD | Mean prevention |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | Legacy | 30142.00 | 0.00 | 30142.00 | 574461.84 | 234675.9989 | 29.89% |
| 0 | Candidate | 30142.00 | 0.00 | 30142.00 | 537858.32 | 217495.6638 | 36.12% |
| 10 | Legacy | 30142.00 | 1812.00 | 31954.00 | 576273.84 | 234053.5106 | 29.89% |
| 10 | Candidate | 30142.00 | 920.80 | 31062.80 | 538779.12 | 217172.3872 | 36.12% |
| 25 | Legacy | 30142.00 | 4530.00 | 34672.00 | 578991.84 | 233125.1094 | 29.89% |
| 25 | Candidate | 30142.00 | 2302.00 | 32444.00 | 540160.32 | 216689.1803 | 36.12% |
| 50 | Legacy | 30142.00 | 9060.00 | 39202.00 | 583521.84 | 231592.1804 | 29.89% |
| 50 | Candidate | 30142.00 | 4604.00 | 34746.00 | 542462.32 | 215888.4243 | 36.12% |
| 100 | Legacy | 30142.00 | 18120.00 | 48262.00 | 592581.84 | 228581.6449 | 29.89% |
| 100 | Candidate | 30142.00 | 9208.00 | 39350.00 | 547066.32 | 214304.3510 | 36.12% |
| 200 | Legacy | 30142.00 | 36240.00 | 66382.00 | 610701.84 | 222792.2340 | 29.89% |
| 200 | Candidate | 30142.00 | 18416.00 | 48558.00 | 556274.32 | 211207.7807 | 36.12% |

### EXP-03A candidate-vs-legacy summary by probe cost

Each count is across the 50 profile/seed/capacity base cells.

| Probe cost | Cost lower/equal/higher | Friction lower/equal/higher | Probe friction lower/equal/higher | Mean cost delta | Min/max cost delta | Mean friction delta | Min/max friction delta |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 50/0/0 | 0/50/0 | 0/50/0 | -36603.53 | -71441.50/-13081.85 | 0.00 | 0.00/0.00 |
| 10 | 50/0/0 | 50/0/0 | 50/0/0 | -37494.72 | -71991.50/-13761.85 | -891.20 | -1960.00/-540.00 |
| 25 | 50/0/0 | 50/0/0 | 50/0/0 | -38831.53 | -72816.50/-14781.85 | -2228.00 | -4900.00/-1350.00 |
| 50 | 50/0/0 | 50/0/0 | 50/0/0 | -41059.53 | -74191.50/-16481.85 | -4456.00 | -9800.00/-2700.00 |
| 100 | 50/0/0 | 50/0/0 | 50/0/0 | -45515.53 | -76941.50/-19881.85 | -8912.00 | -19600.00/-5400.00 |
| 200 | 50/0/0 | 50/0/0 | 50/0/0 | -54427.53 | -82441.50/-26681.85 | -17824.00 | -39200.00/-10800.00 |

### EXP-03A profile-level sensitivity

Each profile has 10 base cells: five seeds × two capacities.

| Profile | Probe cost | Cost lower/equal/higher | Friction lower/equal/higher | Mean cost delta | Mean friction delta |
|---|---:|---:|---:|---:|---:|
| EQUAL_FAMILY | 0 | 10/0/0 | 0/10/0 | -48291.42 | 0.00 |
| EQUAL_FAMILY | 10 | 10/0/0 | 10/0/0 | -49033.42 | -742.00 |
| EQUAL_FAMILY | 25 | 10/0/0 | 10/0/0 | -50146.42 | -1855.00 |
| EQUAL_FAMILY | 50 | 10/0/0 | 10/0/0 | -52001.42 | -3710.00 |
| EQUAL_FAMILY | 100 | 10/0/0 | 10/0/0 | -55711.42 | -7420.00 |
| EQUAL_FAMILY | 200 | 10/0/0 | 10/0/0 | -63131.42 | -14840.00 |
| HARD_NEGATIVE_DOMINANT | 0 | 10/0/0 | 0/10/0 | -15064.06 | 0.00 |
| HARD_NEGATIVE_DOMINANT | 10 | 10/0/0 | 10/0/0 | -16900.06 | -1836.00 |
| HARD_NEGATIVE_DOMINANT | 25 | 10/0/0 | 10/0/0 | -19654.06 | -4590.00 |
| HARD_NEGATIVE_DOMINANT | 50 | 10/0/0 | 10/0/0 | -24244.06 | -9180.00 |
| HARD_NEGATIVE_DOMINANT | 100 | 10/0/0 | 10/0/0 | -33424.06 | -18360.00 |
| HARD_NEGATIVE_DOMINANT | 200 | 10/0/0 | 10/0/0 | -51784.06 | -36720.00 |
| LEGITIMATE_DOMINANT | 0 | 10/0/0 | 0/10/0 | -15064.06 | 0.00 |
| LEGITIMATE_DOMINANT | 10 | 10/0/0 | 10/0/0 | -15798.06 | -734.00 |
| LEGITIMATE_DOMINANT | 25 | 10/0/0 | 10/0/0 | -16899.06 | -1835.00 |
| LEGITIMATE_DOMINANT | 50 | 10/0/0 | 10/0/0 | -18734.06 | -3670.00 |
| LEGITIMATE_DOMINANT | 100 | 10/0/0 | 10/0/0 | -22404.06 | -7340.00 |
| LEGITIMATE_DOMINANT | 200 | 10/0/0 | 10/0/0 | -29744.06 | -14680.00 |
| NETWORK_ABUSE_HEAVY | 0 | 10/0/0 | 0/10/0 | -64817.82 | 0.00 |
| NETWORK_ABUSE_HEAVY | 10 | 10/0/0 | 10/0/0 | -65389.82 | -572.00 |
| NETWORK_ABUSE_HEAVY | 25 | 10/0/0 | 10/0/0 | -66247.82 | -1430.00 |
| NETWORK_ABUSE_HEAVY | 50 | 10/0/0 | 10/0/0 | -67677.82 | -2860.00 |
| NETWORK_ABUSE_HEAVY | 100 | 10/0/0 | 10/0/0 | -70537.82 | -5720.00 |
| NETWORK_ABUSE_HEAVY | 200 | 10/0/0 | 10/0/0 | -76257.82 | -11440.00 |
| SOCIAL_ENGINEERING_HEAVY | 0 | 10/0/0 | 0/10/0 | -39780.27 | 0.00 |
| SOCIAL_ENGINEERING_HEAVY | 10 | 10/0/0 | 10/0/0 | -40352.27 | -572.00 |
| SOCIAL_ENGINEERING_HEAVY | 25 | 10/0/0 | 10/0/0 | -41210.27 | -1430.00 |
| SOCIAL_ENGINEERING_HEAVY | 50 | 10/0/0 | 10/0/0 | -42640.27 | -2860.00 |
| SOCIAL_ENGINEERING_HEAVY | 100 | 10/0/0 | 10/0/0 | -45500.27 | -5720.00 |
| SOCIAL_ENGINEERING_HEAVY | 200 | 10/0/0 | 10/0/0 | -51220.27 | -11440.00 |

No candidate total-cost regression occurred at any tested probe-cost value.
At that stage, the candidate remained **experimental / not promoted**. At probe cost zero,
total legitimate friction is equal because only intervention friction remains;
from any positive tested cost onward, the candidate has lower legitimate probe
and total friction. The candidate's modeled-cost advantage increases as the
assumed probe cost increases because it requests fewer legitimate probes.

These are controlled prototype accounting assumptions. They are not actual
customer-friction estimates, measured upay friction, monetary willingness to
pay, or production economics.

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

How sensitive is the candidate-versus-legacy result to the intervention
protection, friction, and operational-cost assumptions that directly influence
intervention selection?

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
- EXP-03A varies Context Probe accounting cost only; intervention-selection
  assumptions remain fixed.
- No actual production upay data is integrated.
- No production causal intervention effects are measured.

## EXP-03B Intervention-Assumption Sensitivity

Research question: does the Decision-Relevant Context Probe candidate retain
its advantages over the legacy Context Probe when prototype intervention
protection, customer-friction, and operational-cost assumptions vary?

The experiment used the five EXP-02 mixture profiles, seeds
`7, 21, 42, 84, 126`, capacities `5, 20`, count `600`, and seven assumption
profiles: `BASELINE`, `LOWER_PROTECTION`, `HIGHER_PROTECTION`,
`HIGH_CUSTOMER_FRICTION`, `HIGH_OPERATIONS_COST`, `HIGH_REVIEW_COST`, and
`CONSERVATIVE_STRESS`. This produced **350 controlled cells** and **700
strategy runs**. Each fixed mixture/seed population was reused across
capacities, assumptions, and both strategies. The candidate's
decision-relevance checks and final intervention selection used the same
assumption-specific experiment policy.

All transformations were applied to the repository baseline profiles:
`LOWER_PROTECTION` multiplied non-zero protection by `0.80`;
`HIGHER_PROTECTION` multiplied protection by `1.20` and capped it at `0.95`;
`HIGH_CUSTOMER_FRICTION` multiplied friction by `2.0`;
`HIGH_OPERATIONS_COST` multiplied operations cost by `2.0`;
`HIGH_REVIEW_COST` multiplied only human-review operations cost by `3.0`; and
`CONSERVATIVE_STRESS` combined protection `0.80`, friction `1.50`, and
operations `2.00`. `ALLOW` remained all zero and all materialized values were
validated as non-negative and within protection bounds.

Each assumption profile covers **50 controlled cells**. Within every
assumption, the candidate used fewer probes in **50/50** cells, had better
prevention in **50/50** cells, lower legitimate total friction in **50/50**
cells, and lower modeled cost in **50/50** cells. Across all seven
assumptions, the global summary covers **350 controlled cells** and reports
fewer probes in **350/350**, better prevention in **350/350**, lower legitimate
total friction in **350/350**, and lower modeled cost in **350/350**. Mean
prevention
deltas ranged from `+0.0551` (`HIGH_OPERATIONS_COST`) to `+0.0799`
(`HIGHER_PROTECTION`). Mean modeled-cost deltas ranged from `-54386.18`
(`HIGHER_PROTECTION`) to `-24191.17` (`CONSERVATIVE_STRESS`). These are
candidate-minus-legacy deltas.

The artifact preserves both scopes: `candidate_summaries` contains one
50-cell summary per assumption, while `global_candidate_summary` contains the
derived 350-cell aggregate. The console labels identify the same distinction.

| Assumption | Candidate mean requested / allocated reviews | Legacy mean requested / allocated reviews | Candidate full-capacity cells |
|---|---:|---:|---:|
| BASELINE | 5.80 / 4.46 | 0.64 / 0.64 | 10 |
| LOWER_PROTECTION | 0 / 0 | 0 / 0 | 0 |
| HIGHER_PROTECTION | 0 / 0 | 0 / 0 | 0 |
| HIGH_CUSTOMER_FRICTION | 0 / 0 | 0 / 0 | 0 |
| HIGH_OPERATIONS_COST | 0 / 0 | 0 / 0 | 0 |
| HIGH_REVIEW_COST | 0 / 0 | 0 / 0 | 0 |
| CONSERVATIVE_STRESS | 0 / 0 | 0 / 0 | 0 |

The baseline candidate maximum requested and allocated review counts were
both `16`; the legacy maximum was `3`. No allocation exceeded capacity. The
full materialized artifact is
`artifacts/context_probe_intervention_sensitivity.json` and is intentionally
untracked. No candidate prevention, legitimate-friction, or modeled-cost
regressions occurred in the tested grid.

Decision-change analysis showed that assumption changes alter policy behavior,
not merely accounting: the highest mean requested-action change rates were
approximately `50.33%` for the candidate and `45.79%` for legacy under
`CONSERVATIVE_STRESS`.
These results are synthetic sensitivity evidence, not measured intervention
effectiveness, customer harm, production economics, or a promotion decision.

## Promotion

The Decision-Relevant Context Probe has been promoted as the canonical
AegisPay prototype Context Probe policy after consistent synthetic validation
across seed, capacity, scenario-mixture, probe-friction, and
intervention-assumption sensitivity experiments (EXP-01 through EXP-03B).

`AegisPayDecisionService()` now defaults to
`DecisionRelevantContextProbeService`. `ContextProbeService` remains available
as the explicit legacy baseline for experiments, ablations, historical
comparison, and regression analysis. Comparative experiment constructors
explicitly inject their intended legacy or candidate policy.

This promotion applies to the hackathon prototype only and does not constitute
production validation. The evidence remains synthetic prototype evidence, not
measured production fraud reduction, intervention effectiveness, customer
behavior, or production economics.

## Next Research Question

What additional evidence and governance are required before considering the
canonical prototype policy for any non-synthetic evaluation?

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
`artifacts/` directory. Do not promote the candidate automatically. The next research task should
address whether the accumulated evidence justifies promotion, keeping ground
truth evaluation-only and reporting prevention, friction, review demand, and
modeled cost together.
M  DEV_STATUS.md
?? artifacts/
?? experiments/management/commands/run_context_probe_intervention_sensitivity.py
?? experiments/services/intervention_assumptions.py
?? experiments/services/probe_intervention_sensitivity.py
?? experiments/tests/test_intervention_assumptions.py
?? experiments/tests/test_probe_intervention_sensitivity.py
?? experiments/tests/test_probe_intervention_sensitivity_command.py