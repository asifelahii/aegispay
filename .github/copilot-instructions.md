# AegisPay Copilot Instructions

## Project purpose

AegisPay is an Intent-Aware Adaptive Scam Intervention system for Mobile
Financial Services. It combines transaction and behavioral risk, beneficiary
network intelligence, selectively acquired scam context, minimum-effective
intervention selection, and constrained human review.

The core research hypothesis is whether selective scam-context acquisition plus
context-aware intervention selection can reduce simulated scam losses with less
legitimate-user friction at the same review capacity as a conventional
threshold-based policy. This is a hypothesis, not a proven conclusion.

## Architecture constraints

- Keep the current Django-first, modular monolith architecture.
- Use thin Django interfaces and views, application services, typed contracts,
  and deterministic experiment services.
- Current runtime components include transaction normalization and enrichment,
  recipient/network features, a transparent rules risk engine, Context Probe
  and context-risk adjustment, intervention policy, review-capacity allocation,
  and portfolio decisions.
- Do not introduce FastAPI, Angular, React/Next.js, microservices, Redis,
  Celery, or Kafka unless a future task explicitly authorizes an architectural
  change.
- Do not describe an individual technique as novel or claim AegisPay is
  world-first. The contribution is the integrated decision workflow.

## Scope discipline

- Implement only the requested task.
- Inspect relevant existing code before editing.
- Avoid unrelated refactors and casual public-contract renames.
- Preserve backward compatibility unless explicitly told otherwise.
- Do not start the next task automatically.
- Do not modify UI/UX (templates, HTMX, Tailwind, dashboards, charts, graph
  visualization, or analyst/customer screens) without explicit authorization.

## Ground-truth leakage prevention

Synthetic labels such as `is_scam`, `scam_type`, and scenario labels are for
training when explicitly appropriate, offline evaluation, metrics, and
experiment analysis only. They must never be runtime inputs to risk scoring,
Context Probe selection, graph-risk logic, intervention selection, or customer
decisions. Treat any possible target leakage as a blocking issue.

## Experiment and data honesty

- Synthetic scenarios, intervention effects, protection rates, friction costs,
  operations costs, thresholds, and distributions are prototype assumptions.
- Call results a synthetic benchmark, simulation result, or
  scenario-coverage evaluation. Do not present them as real upay prevalence,
  production performance, measured customer behavior, measured intervention
  effectiveness, fraud losses, or production economics.
- Controlled comparisons must use the same scenario population, seed when
  intended, review capacity, and evaluation-only ground truth.
- Preserve reproducibility and compare prevention, friction, review demand, and
  modeled cost together. Do not tune assumptions merely to beat a baseline;
  failed experiments remain valid results.
- Do not promote an experimental candidate into runtime policy without an
  explicit research or product decision.

## Safety and policy integrity

Preserve human oversight, explainability, transparent assumptions, and
responsible automation. Do not implement autonomous permanent wallet freezing
or unsupported harmful automation. The intervention family is expected to
include ALLOW, CONTEXTUAL_WARNING, SCAM_WARNING, VERIFY, COOLING_PERIOD, and
HUMAN_REVIEW; step-up authentication is future work unless authorized.

## Testing discipline

For implementation tasks, run focused tests first, then relevant application
or experiment tests, then the full suite before a validated commit unless the
user says otherwise. Also run:

- `python manage.py check`
- `python manage.py makemigrations --check`

Diagnose failures rather than changing production logic blindly. Do not report
success while tests are failing.

## Git discipline

- Do not commit or push unless explicitly instructed.
- Do not commit `artifacts/` unless explicitly instructed.
- Preserve meaningful history and avoid noisy experimental commits.
- Suggest one concise conventional commit message in the completion report.

## Completion reports

For documentation or implementation tasks, report:

1. task status;
2. repository inspection and discrepancies;
3. files created or changed and their purpose;
4. application-code changes;
5. validation performed and results;
6. current state captured;
7. risks or observations;
8. one suggested commit message.

