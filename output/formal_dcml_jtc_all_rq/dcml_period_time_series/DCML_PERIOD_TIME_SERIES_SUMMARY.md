# DCML Period Time-Series Summary

Periods are inferred from DCML metadata composition years.

## Period Coverage

- `classical_period`: 211 pieces, 279901 events; corpora: ABC, beethoven, mozart
- `romantic_period`: 196 pieces, 111462 events; corpora: chopin, dvorak, grieg, liszt, medtner, schumann, tchaikovsky

## High-Surprisal Thresholds

- `classical_period`: 10.280
- `romantic_period`: 10.515

## RQ1 Within-Classical Curve Shape

- `mean_romantic_minus_classical`: 0.716
- `rms_curve_difference`: 0.853
- `max_romantic_excess`: 1.920 at position 19
- `max_classical_excess`: -0.364 at position 0
- `signed_area_romantic_minus_classical`: 0.716

## RQ1 Period Time-Structure Effects

- `mean_surprisal`: classical=7.116, romantic=7.855, romantic-classical=0.739, d=0.998
- `sd_surprisal`: classical=2.923, romantic=2.646, romantic-classical=-0.277, d=-0.889
- `curve_range`: classical=13.023, romantic=11.605, romantic-classical=-1.418, d=-0.764
- `end_minus_start`: classical=-0.270, romantic=0.048, romantic-classical=0.317, d=0.282
- `linear_slope`: classical=-0.152, romantic=0.047, romantic-classical=0.199, d=0.219
- `mean_local_variance`: classical=6.643, romantic=6.049, romantic-classical=-0.593, d=-0.432
- `max_local_variance`: classical=16.227, romantic=12.273, romantic-classical=-3.954, d=-1.029
- `peak_rate`: classical=0.085, romantic=0.082, romantic-classical=-0.003, d=-0.112
- `changepoint_rate`: classical=0.016, romantic=0.018, romantic-classical=0.002, d=0.349
- `mean_high_run`: classical=1.158, romantic=1.127, romantic-classical=-0.031, d=-0.157
- `max_high_run`: classical=4.238, romantic=3.537, romantic-classical=-0.701, d=-0.138
- `state_entropy`: classical=2.240, romantic=2.204, romantic-classical=-0.037, d=-0.389
- `entropy_rate_order1`: classical=2.068, romantic=2.002, romantic-classical=-0.066, d=-0.535
- `entropy_rate_order2`: classical=1.922, romantic=1.680, romantic-classical=-0.243, d=-1.207
- `same_state_transition_rate`: classical=0.318, romantic=0.296, romantic-classical=-0.022, d=-0.430
- `dominant_transition_rate`: classical=0.136, romantic=0.124, romantic-classical=-0.012, d=-0.238

## RQ2 Period Boundary Curve Shape

- `mean_romantic_minus_classical`: 0.999
- `rms_curve_difference`: 1.055
- `max_romantic_excess`: 1.839 at rel 3
- `max_classical_excess`: 0.243 at rel 1
- `signed_area_romantic_minus_classical`: 0.999

## RQ2 Period Boundary Effects

- `boundary_curve_range`: classical=3.939, romantic=4.455, romantic-classical=0.516, d=0.382
- `boundary_value`: classical=8.275, romantic=8.813, romantic-classical=0.539, d=0.465
- `peak_relative_event`: classical=-0.571, romantic=-0.370, romantic-classical=0.201, d=0.034
- `post_minus_pre`: classical=0.213, romantic=0.236, romantic-classical=0.022, d=0.034
- `boundary_core_lift_vs_far`: classical=0.554, romantic=0.338, romantic-classical=-0.216, d=-0.260
- `boundary_local_variance_lift_vs_far`: classical=0.474, romantic=-0.059, romantic-classical=-0.533, d=-0.525
- `boundary_lift_vs_unigram`: classical=-0.018, romantic=-0.253, romantic-classical=-0.235, d=-0.184
- `boundary_lift_vs_shuffled`: classical=-0.800, romantic=-0.476, romantic-classical=0.325, d=0.336
- `normalized_boundary_z`: classical=1.308, romantic=0.925, romantic-classical=-0.382, d=-0.394
- `high_event_boundary_enrichment`: classical=1.062, romantic=0.920, romantic-classical=-0.142, d=-0.248
- `peak_boundary_enrichment`: classical=1.092, romantic=0.927, romantic-classical=-0.165, d=-0.287
- `changepoint_boundary_enrichment`: classical=1.899, romantic=1.337, romantic-classical=-0.562, d=-0.442