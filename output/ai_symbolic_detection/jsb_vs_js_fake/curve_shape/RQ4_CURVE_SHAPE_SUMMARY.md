# RQ4 Curve Shape Summary: jsb_vs_js_fake

Human source: `jsb`
AI source: `js_fake`
Human high-surprisal threshold q=0.9: `8.535`

## Curve Shape Distance

- `mean_ai_minus_human`: 2.855
- `rms_curve_difference`: 2.905
- `max_ai_excess`: 4.078 at t=0.99
- `max_human_excess`: -0.355 at t=0.00
- `signed_area_ai_minus_human`: 2.855

## Run-Length Summary

### human
- `high_state_rate`: 0.104
- `mean_high_run`: 1.073
- `max_high_run`: 1.340
- `mean_low_run`: 11.248
### ai
- `high_state_rate`: 0.388
- `mean_high_run`: 1.456
- `max_high_run`: 3.880
- `mean_low_run`: 2.252

## Changepoint Summary

### human
- `changepoint_rate`: 0.013
- `mean_changepoint_time`: 0.305
### ai
- `changepoint_rate`: 0.021
- `mean_changepoint_time`: 0.460

## Sequence Dependency Summary

- `state_entropy`: human=2.139, AI=1.749, AI-human=-0.390, d=-1.952
- `entropy_rate_order1`: human=1.723, AI=1.513, AI-human=-0.209, d=-1.131
- `entropy_rate_order2`: human=0.900, AI=1.166, AI-human=0.266, d=1.560
- `predictability_gain_order1`: human=0.417, AI=0.236, AI-human=-0.181, d=-1.315
- `predictability_gain_order2`: human=0.823, AI=0.348, AI-human=-0.475, d=-2.447
- `same_state_transition_rate`: human=0.276, AI=0.283, AI-human=0.007, d=0.085
- `dominant_transition_rate`: human=0.155, AI=0.227, AI-human=0.072, d=1.334