# RQ4 Special Position Summary: jsb_vs_cocochorales_test1

Human source: `jsb`
AI source: `cocochorales`
Human high-surprisal threshold q=0.9: `8.524`
Boundary window: `+/-4` events

## Mean Surprisal by Special Position

- `opening_10pct`: human=5.142, AI=8.829, AI-human=3.687
- `middle_10pct`: human=5.265, AI=9.254, AI-human=3.989
- `closing_10pct`: human=4.946, AI=8.495, AI-human=3.548
- `annotated_boundary_exact`: human=5.443, AI=9.163, AI-human=3.720
- `annotated_boundary_zone_pm4`: human=5.052, AI=9.048, AI-human=3.996
- `pre_boundary_4`: human=5.061, AI=9.021, AI-human=3.960
- `post_boundary_4`: human=5.065, AI=9.122, AI-human=4.057
- `far_from_annotated_boundary`: human=6.039, AI=9.077, AI-human=3.038

## Alignment Effects

- `boundary_zone_surprisal_lift`: human=-0.483, AI=0.193, AI-human=0.676, d=0.497
- `high_event_boundary_enrichment`: human=0.935, AI=0.525, AI-human=-0.410, d=-0.933
- `peak_boundary_enrichment`: human=0.945, AI=0.575, AI-human=-0.369, d=-0.770
- `changepoint_boundary_enrichment`: human=0.647, AI=0.000, AI-human=-0.647, d=-1.773
- `closing_minus_opening_surprisal`: human=-0.306, AI=-0.327, AI-human=-0.021, d=-0.008

## Label-Level Alignment Means

### human
- `boundary_zone_event_rate`: 0.956
- `boundary_zone_surprisal_lift`: -0.483
- `high_event_boundary_enrichment`: 0.935
- `peak_boundary_enrichment`: 0.945
- `changepoint_boundary_enrichment`: 0.647
- `closing_minus_opening_surprisal`: -0.306
### ai
- `boundary_zone_event_rate`: 0.232
- `boundary_zone_surprisal_lift`: 0.193
- `high_event_boundary_enrichment`: 0.525
- `peak_boundary_enrichment`: 0.575
- `changepoint_boundary_enrichment`: 0.000
- `closing_minus_opening_surprisal`: -0.327