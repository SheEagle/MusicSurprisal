# RQ4 Bidirectional Expectation Summary: jsb_vs_js_fake

Human source: `jsb`
AI source: `js_fake`

## Train/Eval Splits

- `human` train: 229 pieces, 10729 events; eval: 153 pieces, 7269 events
- `ai` train: 350 pieces, 26106 events; eval: 150 pieces, 10982 events

## Cell Means

- model=`ai`, eval=`ai`: mean=5.393, p90=8.587, pieces=150
- model=`ai`, eval=`human`: mean=6.602, p90=9.264, pieces=153
- model=`human`, eval=`ai`: mean=7.835, p90=11.891, pieces=150
- model=`human`, eval=`human`: mean=5.027, p90=8.205, pieces=153

## Direction Tests

- `human_model_ai_minus_human`: within=5.027, cross=7.835, cross-within=2.808; p90 diff=3.686
- `ai_model_human_minus_ai`: within=5.393, cross=6.602, cross-within=1.209; p90 diff=0.677