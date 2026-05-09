# RQ3 LSTM Harmony Summary

This optional analysis compares three long-context neural sequence models:

- Model A: melody-only LSTM. Previous pitch classes -> current pitch class.
- Model B: melody + current harmony. Pitch-history LSTM plus current T/D/S/other at the output layer.
- Model C: melody + harmony history sequence. Pitch and T/D/S/other are both recurrent inputs, so the hidden state can encode harmonic progression.

Gain A->B = Model A surprisal minus Model B surprisal.
Gain A->C = Model A surprisal minus Model C surprisal.
Gain B->C = Model B surprisal minus Model C surprisal.
Positive gain means the richer harmony model improved prediction.

Training: epochs=6, hidden_size=64, chunk_len=64.

## Period Summary

- `classical_period`: A=2.7447, B=2.7511, C=2.6928, A->B=-0.0064, A->C=0.0520, B->C=0.0583
- `romantic_period`: A=2.9507, B=2.9506, C=2.9420, A->B=0.0001, A->C=0.0087, B->C=0.0087

## By Harmonic Function

- `classical_period` / `D`: A->B=-0.0151, A->C=0.0269, B->C=0.0420, events=43077
- `classical_period` / `S`: A->B=-0.0079, A->C=0.0467, B->C=0.0546, events=11382
- `classical_period` / `T`: A->B=0.0063, A->C=0.0926, B->C=0.0864, events=29612
- `classical_period` / `other`: A->B=0.0082, A->C=0.0036, B->C=-0.0046, events=1345
- `romantic_period` / `D`: A->B=-0.0035, A->C=0.0108, B->C=0.0144, events=17883
- `romantic_period` / `S`: A->B=-0.0008, A->C=-0.0070, B->C=-0.0062, events=6472
- `romantic_period` / `T`: A->B=0.0042, A->C=0.0154, B->C=0.0112, events=11572
- `romantic_period` / `other`: A->B=0.0245, A->C=-0.0050, B->C=-0.0294, events=896