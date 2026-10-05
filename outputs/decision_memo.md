# Synthetic pricing decision memo

24,000 independent quotes; train/validation split fixed before analysis.

| Corridor | Selected multiplier | Price elasticity | Predicted CM / quote | Held-out selected-arm CM / quote |
|---|---:|---:|---:|---:|
| Market-A | 1.0 | -0.80 | $2.62 | $2.63 |
| Market-B | 1.0 | -2.08 | $1.94 | $1.90 |
| Market-C | 1.0 | -0.76 | $3.79 | $3.82 |

The recommendation maximizes immediate contribution within observed price support, subject to the model conversion guardrail. This is a hypothesis for a follow-up test, not a production rollout decision.

Next experiment: randomize eligible customers between current and selected total price; freeze allocation and exclusions, size on contribution variance, cluster on customer if repeated quotes exist, and monitor conversion, complaints and 30-day retention. No horizon or LTV extrapolation is justified by this dataset.
