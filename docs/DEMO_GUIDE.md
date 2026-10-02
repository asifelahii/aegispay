# AegisPay Demo Guide

## Before Demo

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py check
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The demo is deterministic and simulated; no
real payment is transferred.

## Demo Flow — Approximately 3–5 Minutes

### 0:00–0:30 — Problem

Open `/dashboard/` and say:

> AegisPay is not only asking whether a transaction is risky. It is deciding
> what should happen next while balancing customer friction, modeled loss, and
> constrained review capacity.

Point to the proposition and the Demo Journey. Mention that the evidence is
synthetic prototype evidence.

### 0:30–1:30 — Customer Flow

Open `/demo/`. Select **Guided / impersonation risk** and submit a payment.
The customer-facing page presents one Security Check because the answer can
change the intervention.

Answer **Yes**. Explain:

> The system asked one targeted question rather than presenting a generic
> questionnaire. The answer adds context; it does not replace the objective
> transaction evidence.

The result is an additional review recommendation. Use **View Analyst
Explanation**.

### 1:30–2:15 — Explainability

On `/dashboard/transactions/TX-8420/`, point out:

- transaction details;
- rules-based risk score and reason contributions;
- behavioral intelligence;
- recipient-network indicators;
- the Context Probe question, answer, and decision impact;
- the selected intervention and prototype assumptions.

Say:

> This is deliberately transparent. The analyst can see what happened, why it
> mattered, what context was acquired, and why the action was selected.

Click **Inspect Recipient Network**.

### 2:15–3:00 — Network

On `/dashboard/network/?scenario=high-risk`, select graph nodes or use the
keyboard. Show fan-in, fan-out, pass-through, cash-out velocity, and the
historical event table.

Say:

> Network signals increase concern under prototype rules; they do not prove
> that a wallet is fraudulent. The graph is a synthetic presentation of
> historical relationships, not a production graph database.

### 3:00–4:00 — Evidence

Open `/dashboard/experiments/`. Start with the reference comparison and call
out the explicit review-demand trade-off: **3 to 14** allocated reviews.
Then point to EXP-01 through EXP-03B.

Emphasize:

> The candidate used fewer probes and had better synthetic benchmark
> outcomes across the tested dimensions, but the result is not production
> validation and review demand increased.

### 4:00–4:30 — Limitations / Close

Close with:

> AegisPay currently validates a transparent rules, network, context, and
> intervention workflow on synthetic scenarios. It does not claim real fraud
> reduction, real customer behavior, production economics, or an ML result.

## Fallback Path

If live form interaction fails, open these direct routes:

1. `/dashboard/`
2. `/dashboard/transactions/TX-8420/`
3. `/dashboard/network/?scenario=high-risk`
4. `/dashboard/experiments/`

For the no-probe story, use `/demo/`, select **Strong evidence**, and explain
that existing evidence is already sufficient. For the low-friction story,
select **Normal payment** and show the simulated success state.

## Scenario Talking Points

| Scenario | Point to demonstrate |
|---|---|
| Normal payment | No unnecessary security friction |
| Guided / impersonation risk | One decision-relevant question changes intervention |
| Strong evidence | No unnecessary question when evidence is sufficient |

## Safety Notes

Do not describe synthetic values as real losses, savings, prevalence,
protection rates, or customer behavior. Do not claim the network page proves
fraud. Do not imply that the demo transfers money.
