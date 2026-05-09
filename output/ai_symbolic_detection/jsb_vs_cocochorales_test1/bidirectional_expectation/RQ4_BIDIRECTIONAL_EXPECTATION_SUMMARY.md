# RQ4 Bidirectional Expectation Summary: jsb_vs_cocochorales_test1

Human source: `jsb`
AI source: `cocochorales`

## Train/Eval Splits

- `human` train: 200 pieces, 9405 events; eval: 153 pieces, 7269 events
- `ai` train: 140 pieces, 3237 events; eval: 60 pieces, 1292 events

## Cell Means

- model=`ai`, eval=`ai`: mean=6.594, p90=8.608, pieces=60
- model=`ai`, eval=`human`: mean=7.918, p90=10.606, pieces=153
- model=`human`, eval=`ai`: mean=9.210, p90=12.775, pieces=60
- model=`human`, eval=`human`: mean=5.131, p90=8.289, pieces=153

## Direction Tests

- `human_model_ai_minus_human`: within=5.131, cross=9.210, cross-within=4.079; p90 diff=4.486
- `ai_model_human_minus_ai`: within=6.594, cross=7.918, cross-within=1.324; p90 diff=1.999