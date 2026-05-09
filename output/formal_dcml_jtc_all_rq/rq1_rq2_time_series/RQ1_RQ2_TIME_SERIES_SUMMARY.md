# RQ1/RQ2 Time-Series Summary

Events: `data\events_dcml_jtc_all_rq.csv`
High-surprisal threshold quantile: `0.9`

## Source Thresholds

- `dcml`: 10.326
- `jtc`: 10.107

## RQ1 Mean-Scale Caveat Diagnostics

- `dcml`: train_tokens=294846, vocab=683, unique_pitches=79, contexts=39678, OOV=0.0005, backoff=0.1212, full_context_hit=0.8788
- `jtc`: train_tokens=13794, vocab=402, unique_pitches=52, contexts=3958, OOV=0.0383, backoff=0.4454, full_context_hit=0.5546

## RQ1 Whole-Piece Curve Shape

- `mean_jtc_minus_dcml`: 0.603
- `rms_curve_difference`: 0.711
- `max_jtc_excess`: 1.622 at position 87
- `max_dcml_excess`: -0.318 at position 54
- `signed_area_jtc_minus_dcml`: 0.603

## RQ1 Time-Structure Effects

- `mean_surprisal`: dcml=7.432, jtc=8.058, jtc-dcml=0.625, d=0.785
- `sd_surprisal`: dcml=2.699, jtc=2.253, jtc-dcml=-0.447, d=-1.086
- `curve_range`: dcml=11.659, jtc=9.633, jtc-dcml=-2.026, d=-0.929
- `end_minus_start`: dcml=-0.112, jtc=-0.032, jtc-dcml=0.080, d=0.073
- `linear_slope`: dcml=-0.111, jtc=0.082, jtc-dcml=0.193, d=0.228
- `mean_local_variance`: dcml=6.099, jtc=4.997, jtc-dcml=-1.102, d=-0.661
- `max_local_variance`: dcml=12.854, jtc=8.205, jtc-dcml=-4.649, d=-1.221
- `peak_rate`: dcml=0.080, jtc=0.100, jtc-dcml=0.020, d=0.375
- `changepoint_rate`: dcml=0.017, jtc=0.021, jtc-dcml=0.004, d=0.479
- `mean_high_run`: dcml=1.117, jtc=1.181, jtc-dcml=0.064, d=0.208
- `max_high_run`: dcml=3.228, jtc=1.649, jtc-dcml=-1.580, d=-0.531
- `state_entropy`: dcml=2.198, jtc=1.600, jtc-dcml=-0.597, d=-2.972
- `entropy_rate_order1`: dcml=1.989, jtc=1.380, jtc-dcml=-0.609, d=-2.717
- `entropy_rate_order2`: dcml=1.698, jtc=1.067, jtc-dcml=-0.631, d=-2.334
- `same_state_transition_rate`: dcml=0.300, jtc=0.409, jtc-dcml=0.109, d=1.157
- `dominant_transition_rate`: dcml=0.131, jtc=0.331, jtc-dcml=0.200, d=2.241

## RQ2 Boundary Curve Shape

- `mean_jtc_minus_dcml`: 0.641
- `rms_curve_difference`: 0.731
- `max_jtc_excess`: 1.106 at rel 5
- `max_dcml_excess`: -0.502 at rel 2
- `signed_area_jtc_minus_dcml`: 0.641

## RQ2 Boundary Time-Structure Effects

- `boundary_curve_range`: dcml=4.461, jtc=4.897, jtc-dcml=0.436, d=0.235
- `boundary_value`: dcml=8.386, jtc=9.287, jtc-dcml=0.901, d=0.767
- `peak_relative_event`: dcml=-0.485, jtc=-1.892, jtc-dcml=-1.407, d=-0.252
- `post_minus_pre`: dcml=0.134, jtc=0.093, jtc-dcml=-0.041, d=-0.071
- `boundary_core_lift_vs_far`: dcml=0.481, jtc=0.042, jtc-dcml=-0.439, d=-0.564
- `boundary_local_variance_lift_vs_far`: dcml=0.204, jtc=-0.002, jtc-dcml=-0.206, d=-0.213
- `boundary_lift_vs_unigram`: dcml=-0.352, jtc=-2.441, jtc-dcml=-2.089, d=-1.020
- `boundary_lift_vs_shuffled`: dcml=-0.820, jtc=0.080, jtc-dcml=0.900, d=0.921
- `normalized_boundary_z`: dcml=0.873, jtc=1.122, jtc-dcml=0.249, d=0.255
- `normalized_peak_z`: dcml=1.940, jtc=1.875, jtc-dcml=-0.066, d=-0.140
- `high_event_boundary_enrichment`: dcml=1.075, jtc=1.058, jtc-dcml=-0.017, d=-0.026
- `peak_boundary_enrichment`: dcml=1.128, jtc=1.189, jtc-dcml=0.061, d=0.074
- `changepoint_boundary_enrichment`: dcml=1.431, jtc=0.909, jtc-dcml=-0.522, d=-0.437