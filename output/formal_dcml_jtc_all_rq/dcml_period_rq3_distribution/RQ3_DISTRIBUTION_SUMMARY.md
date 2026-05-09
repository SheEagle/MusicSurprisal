# RQ3 Distribution-Based Harmony Summary

This analysis keeps the melody-only n-gram surprisal fixed and asks whether surprisal differs across harmonic positions.
It avoids the sparsity problem of directly conditioning the n-gram on detailed Roman numerals.

## Coverage

- `classical_period`: 63 pieces, 85416 events
- `romantic_period`: 54 pieces, 36823 events

## Harmonic Function

- `classical_period` / `D`: mean_surprisal=4.701, events=43077
- `classical_period` / `S`: mean_surprisal=4.553, events=11382
- `classical_period` / `T`: mean_surprisal=4.540, events=29612
- `classical_period` / `other`: mean_surprisal=4.439, events=1345
- `romantic_period` / `D`: mean_surprisal=5.056, events=17883
- `romantic_period` / `S`: mean_surprisal=5.084, events=6472
- `romantic_period` / `T`: mean_surprisal=4.903, events=11572
- `romantic_period` / `other`: mean_surprisal=4.852, events=896

## Function Contrasts

- `classical_period` `D_minus_T`: diff=0.161, d=0.064
- `classical_period` `S_minus_T`: diff=0.013, d=0.005
- `classical_period` `D_minus_S`: diff=0.148, d=0.058
- `romantic_period` `D_minus_T`: diff=0.153, d=0.061
- `romantic_period` `S_minus_T`: diff=0.181, d=0.072
- `romantic_period` `D_minus_S`: diff=-0.028, d=-0.011

## Chord Tone

- `classical_period` / `non_chord_tone`: mean_surprisal=4.322, events=18254
- `classical_period` / `chord_tone`: mean_surprisal=4.703, events=67162
- `romantic_period` / `non_chord_tone`: mean_surprisal=5.010, events=10063
- `romantic_period` / `chord_tone`: mean_surprisal=5.007, events=26760

## Chord-Tone Contrasts

- `classical_period` non_chord_minus_chord: diff=-0.380, d=-0.151
- `romantic_period` non_chord_minus_chord: diff=0.003, d=0.001

## Mutual Information

- `all`: I(pitch_class; function)=0.0033 bits, normalized=0.0009
- `classical_period`: I(pitch_class; function)=0.0061 bits, normalized=0.0017
- `romantic_period`: I(pitch_class; function)=0.0056 bits, normalized=0.0016