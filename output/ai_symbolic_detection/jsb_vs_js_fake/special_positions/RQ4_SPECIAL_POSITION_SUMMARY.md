# RQ4 Special Position Summary: jsb_vs_js_fake

Human source: `jsb`
AI source: `js_fake`
Human high-surprisal threshold q=0.9: `8.535`
Boundary window: `+/-4` events

## Mean Surprisal by Special Position

- `opening_10pct`: human=5.081, AI=7.182, AI-human=2.101
- `middle_10pct`: human=5.165, AI=7.948, AI-human=2.783
- `closing_10pct`: human=4.844, AI=8.257, AI-human=3.413
- `annotated_boundary_exact`: human=5.391, AI=7.245, AI-human=1.854
- `annotated_boundary_zone_pm4`: human=4.957, AI=7.904, AI-human=2.947
- `pre_boundary_4`: human=4.978, AI=8.175, AI-human=3.197
- `post_boundary_4`: human=4.966, AI=7.685, AI-human=2.718
- `far_from_annotated_boundary`: human=5.855, AI=7.900, AI-human=2.044

## Alignment Effects

- `boundary_zone_surprisal_lift`: human=-0.473, AI=0.027, AI-human=0.501, d=0.405
- `high_event_boundary_enrichment`: human=0.945, AI=0.992, AI-human=0.047, d=0.179
- `peak_boundary_enrichment`: human=0.949, AI=1.006, AI-human=0.058, d=0.221
- `changepoint_boundary_enrichment`: human=0.633, AI=1.757, AI-human=1.124, d=0.786
- `closing_minus_opening_surprisal`: human=-0.358, AI=1.112, AI-human=1.470, d=0.802

## Label-Level Alignment Means

### human
- `boundary_zone_event_rate`: 0.956
- `boundary_zone_surprisal_lift`: -0.473
- `high_event_boundary_enrichment`: 0.945
- `peak_boundary_enrichment`: 0.949
- `changepoint_boundary_enrichment`: 0.633
- `closing_minus_opening_surprisal`: -0.358
### ai
- `boundary_zone_event_rate`: 0.249
- `boundary_zone_surprisal_lift`: 0.027
- `high_event_boundary_enrichment`: 0.992
- `peak_boundary_enrichment`: 1.006
- `changepoint_boundary_enrichment`: 1.757
- `closing_minus_opening_surprisal`: 1.112