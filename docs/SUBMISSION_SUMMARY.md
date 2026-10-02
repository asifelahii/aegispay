# AegisPay Submission Summary

## Project

**AegisPay — Intent-Aware Adaptive Scam Intervention for Mobile Financial
Services**

## One-Line Pitch

AegisPay combines transaction behavior, recipient-network evidence, and one
selective customer context question to choose a proportionate intervention
under constrained human-review capacity.

## Problem

Risk detection alone does not answer what should happen next. Overly weak
responses can expose customers to loss, while irrelevant questions, excessive
warnings, and scarce manual review create friction and operational cost.

## Solution

AegisPay runs a transparent rules-based assessment, derives recipient-network
signals from historical activity, asks a Decision-Relevant Context Probe only
when it can affect the decision, adjusts risk when context is supplied, and
selects a minimum-effective intervention.

## Core Features

- behavioral transaction intelligence;
- recipient-network intelligence;
- selective customer Security Check;
- Allow through Human Review intervention ladder;
- constrained review-capacity allocation;
- transaction and intervention explainability;
- native SVG network visualization;
- curated experiment evidence dashboard.

## Technical Approach

The implementation is a Django-first modular monolith with typed dataclass
contracts, application services, deterministic synthetic experiments, Django
templates, CSS, and repository-owned JavaScript/SVG. Runtime decisions never
receive evaluation-only ground truth.

## Evidence

In the matched reference configuration (600 scenarios, seed 42, capacity 20),
the canonical probe used 360 probes versus 525 for the legacy probe, with
37.60% versus 30.93% simulated prevention and 711376.80 versus 761733.30
modeled total cost. Allocated reviews increased from 3 to 14.

Across robustness checks, the candidate's directional result persisted in:

- EXP-01: 25/25 seed-capacity cells;
- EXP-02: 50/50 synthetic mixture cells;
- EXP-03A: all six probe-friction points;
- EXP-03B: 350/350 global assumption cells.

## Differentiation

The prototype contribution is the integration of selective context,
transaction evidence, beneficiary-network evidence, adaptive intervention, and
review capacity into one explainable MFS decision workflow. No isolated
technique is claimed as world-first.

## Business / Customer Impact

The intended value proposition is fewer unnecessary customer questions and
more proportionate interventions while preserving analyst oversight. Current
impact is a modeled synthetic benchmark hypothesis, not measured production
impact.

## Scalability / Integration Concept

The modular monolith separates normalization, features, risk, context,
intervention, portfolio allocation, and presentation. A future deployment
could replace synthetic inputs and modeled assumptions with governed data and
calibrated operational estimates without changing the conceptual decision
boundaries.

## Responsible AI

Ground truth is evaluation-only. Explanations expose rules and evidence.
Customer context is selective. Human review remains constrained. No
autonomous permanent wallet freeze, real payment execution, authentication,
or ML claim is included.

## Limitations

Scenarios, weights, protection rates, friction, operations costs, and review
costs are synthetic or modeled. There is no real MFS transaction validation,
observed customer behavior, production analyst workload study, or production
fraud-reduction measurement.

## Repository / Demo Routes

- `/` — analyst entry redirect
- `/demo/` — customer payment demo
- `/dashboard/` — overview
- `/dashboard/transactions/TX-8420/` — explanation
- `/dashboard/network/` — network intelligence
- `/dashboard/experiments/` — validation evidence

See [README.md](../README.md), [ARCHITECTURE.md](ARCHITECTURE.md),
[VALIDATION.md](VALIDATION.md), and [DEMO_GUIDE.md](DEMO_GUIDE.md).
