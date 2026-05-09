# RQ4 Bidirectional Expectation Summary: maestro_matched_excerpt_vs_music_transformer_sample500

Human source: `maestro`
AI source: `music_transformer`

## Train/Eval Splits

- `human` train: 180 pieces, 1087576 events; eval: 500 pieces, 279915 events
- `ai` train: 350 pieces, 194821 events; eval: 150 pieces, 85094 events

## Cell Means

- model=`ai`, eval=`ai`: mean=11.835, p90=12.932, pieces=150
- model=`ai`, eval=`human`: mean=11.603, p90=12.782, pieces=500
- model=`human`, eval=`ai`: mean=11.370, p90=12.633, pieces=150
- model=`human`, eval=`human`: mean=9.966, p90=12.120, pieces=500

## Direction Tests

- `human_model_ai_minus_human`: within=9.966, cross=11.370, cross-within=1.404; p90 diff=0.513
- `ai_model_human_minus_ai`: within=11.835, cross=11.603, cross-within=-0.232; p90 diff=-0.150