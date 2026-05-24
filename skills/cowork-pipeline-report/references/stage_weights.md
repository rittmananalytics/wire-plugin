# Pipeline Stage Probability Weights

Default weights for Rittman Analytics HubSpot pipeline.
Update after every 12–24 closed deals by comparing assigned weight to actual
win rate at that stage.

---

## Default stage weights

| Stage name | Default probability | Notes |
|------------|-------------------|-------|
| Appointment Scheduled | 20% | First meeting booked — qualification not yet started |
| Qualified to Buy | 40% | MEDDIC shows 3+ confirmed elements |
| Presentation Scheduled | 60% | Proposal presented; feedback pending |
| Decision Maker Bought-In | 75% | Economic buyer engaged and positive |
| Contract Sent | 90% | Legal review underway |
| Closed Won | 100% | Signed |
| Closed Lost | 0% | Dead |

---

## Calibration guidance

Once you have 24+ closed deals:

1. For each stage, count how many deals at that stage eventually closed won.
2. Divide by total deals that reached that stage.
3. Replace the default weight with the actual win rate.

Example: if 8 of 20 deals at "Presentation Scheduled" closed won, the
calibrated weight is 40%, not 60%.

Recalibrate quarterly.

---

## At-risk flags (used by pipeline-report skill)

A deal is flagged ⚠️ at risk if any of the following apply:

- No activity logged in >14 days
- Close date has passed without stage change
- Stage probability <30% AND close date is within 30 days
- Amount is null (no commercial value set)

These are heuristics. The CEO should assess each flag in context.
