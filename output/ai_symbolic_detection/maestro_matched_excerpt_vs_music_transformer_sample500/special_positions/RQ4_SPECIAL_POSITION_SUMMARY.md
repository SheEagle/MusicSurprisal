# RQ4 Special Position Summary: maestro_matched_excerpt_vs_music_transformer_sample500

Human source: `maestro`
AI source: `music_transformer`
Human high-surprisal threshold q=0.9: `12.114`
Boundary window: `+/-4` events

## Mean Surprisal by Special Position

- `opening_10pct`: human=9.970, AI=11.255, AI-human=1.285
- `middle_10pct`: human=9.942, AI=11.280, AI-human=1.338
- `closing_10pct`: human=9.963, AI=11.790, AI-human=1.827
- `annotated_boundary_exact`: human=9.434, AI=11.495, AI-human=2.061
- `annotated_boundary_zone_pm4`: human=9.525, AI=11.350, AI-human=1.826
- `pre_boundary_4`: human=9.514, AI=11.303, AI-human=1.789
- `post_boundary_4`: human=9.534, AI=11.388, AI-human=1.854
- `far_from_annotated_boundary`: human=9.954, AI=11.354, AI-human=1.400

## Alignment Effects

- `boundary_zone_surprisal_lift`: human=-0.019, AI=-0.007, AI-human=0.012, d=0.024
- `high_event_boundary_enrichment`: human=0.109, AI=0.486, AI-human=0.377, d=0.609
- `peak_boundary_enrichment`: human=0.111, AI=0.499, AI-human=0.388, d=0.615
- `changepoint_boundary_enrichment`: human=0.151, AI=0.654, AI-human=0.503, d=0.194
- `closing_minus_opening_surprisal`: human=-0.001, AI=0.607, AI-human=0.607, d=0.480

## Label-Level Alignment Means

### human
- `boundary_zone_event_rate`: 0.002
- `boundary_zone_surprisal_lift`: -0.019
- `high_event_boundary_enrichment`: 0.109
- `peak_boundary_enrichment`: 0.111
- `changepoint_boundary_enrichment`: 0.151
- `closing_minus_opening_surprisal`: -0.001
### ai
- `boundary_zone_event_rate`: 0.011
- `boundary_zone_surprisal_lift`: -0.007
- `high_event_boundary_enrichment`: 0.486
- `peak_boundary_enrichment`: 0.499
- `changepoint_boundary_enrichment`: 0.654
- `closing_minus_opening_surprisal`: 0.607