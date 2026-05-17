# IDyOM Cadence Analysis Report

## 1. Research Question

This analysis asks whether different cadence types show systematically different expectation profiles in **melody** and **harmony**, and whether **deceptive cadences (DC)** and **evaded cadences (EC)** can be distinguished by which musical domain carries the surprise.

The central hypothesis is:

> DC should be more harmony-dominant, because the expected harmonic closure is violated.  
> EC should be more melody-dominant or less harmony-dominant, because the cadence is evaded through melodic or phrase-level continuation.

## 2. Data And Method

The analysis uses DCML piano sonatas:

| Composer corpus | Cadence types analyzed | Note |
|---|---|---|
| Mozart piano sonatas | PAC, IAC, HC, DC, EC | PC excluded |
| Beethoven piano sonatas | PAC, IAC, HC, DC, EC | PC excluded because n = 3 |

For each cadence, IDyOM was aligned to a local window:

```text
relative event position = -3, -2, -1, 0, +1, +2, +3
t = 0 is the cadence arrival
```

Two independent original Lisp IDyOM tracks were used:

```text
Melody track:
target = next melody pitch
metric = melody IC / melody entropy

Harmony track:
target = next harmony event
metric = harmony IC / harmony entropy
```

Statistical summaries use **piece-level aggregation** and **piece-level bootstrap confidence intervals**, so pieces with many cadences do not dominate the result.

## 3. Pure Melody IC Curves

![Melody IC profiles](/D:/music/output/idyom_ic_profiles_ci/melody_ic_profiles_mozart_beethoven_ci_ribbon.svg)

The melody-only curves show how surprising the terminal melodic event is around each cadence type.

### Main Melody Findings

In Mozart, EC has the highest terminal melody IC:

| Mozart cadence | Melody IC at t=0 | 95% CI |
|---|---:|---:|
| PAC | 3.03 | [2.83, 3.24] |
| IAC | 3.80 | [3.36, 4.23] |
| HC | 3.37 | [3.13, 3.62] |
| DC | 3.09 | [2.38, 3.87] |
| EC | 5.00 | [4.44, 5.56] |

The significant pairwise contrasts show that Mozart EC has higher melody IC than PAC, IAC, HC, and DC after FDR correction. This supports the interpretation that Mozart EC is strongly associated with **melodic surprise**.

In Beethoven, EC is also melodically high:

| Beethoven cadence | Melody IC at t=0 | 95% CI |
|---|---:|---:|
| PAC | 4.20 | [3.89, 4.50] |
| IAC | 4.36 | [3.98, 4.78] |
| HC | 4.08 | [3.73, 4.41] |
| DC | 3.25 | [2.16, 4.23] |
| EC | 5.68 | [4.21, 7.15] |

The direct Beethoven contrast **DC vs EC** is significant for melody IC:

```text
DC - EC = -2.43
95% CI [-4.25, -0.70]
FDR q = 0.044
```

This means Beethoven EC is significantly more melodically surprising than Beethoven DC.

## 4. Pure Harmony IC Curves

![Harmony IC profiles](/D:/music/output/idyom_ic_profiles_ci/harmony_ic_profiles_mozart_beethoven_ci_ribbon.svg)

The harmony-only curves show how surprising the terminal harmony event is around each cadence type.

### Main Harmony Findings

In Mozart, DC has the highest terminal harmony IC:

| Mozart cadence | Harmony IC at t=0 | 95% CI |
|---|---:|---:|
| PAC | 1.28 | [1.09, 1.48] |
| IAC | 1.92 | [1.49, 2.33] |
| HC | 2.17 | [1.85, 2.53] |
| DC | 5.17 | [3.58, 6.86] |
| EC | 3.76 | [2.56, 5.09] |

Mozart DC is significantly higher than PAC, IAC, and HC in harmony IC. PAC has the lowest harmony IC, which is consistent with PAC as the most conventional harmonic closure.

In Beethoven, the DC harmony effect is much stronger:

| Beethoven cadence | Harmony IC at t=0 | 95% CI |
|---|---:|---:|
| PAC | 1.91 | [1.64, 2.19] |
| IAC | 2.86 | [2.45, 3.31] |
| HC | 3.21 | [2.75, 3.72] |
| DC | 10.07 | [8.04, 12.41] |
| EC | 4.70 | [2.63, 7.13] |

Beethoven DC is significantly higher than PAC, IAC, HC, and EC in harmony IC. The direct DC vs EC contrast is especially strong:

```text
DC - EC = +5.37
95% CI [2.49, 8.38]
FDR q < 0.001
```

This is one of the strongest findings in the whole analysis. Beethoven DC is not just generally surprising; it is specifically **harmonically surprising**.

## 5. Entropy Gradient And Closure Around Cadences

The entropy gradient compares how uncertainty changes at the cadence point. We used:

```text
entropy_gradient_difference = dH_melody - dH_harmony
```

Interpretation:

| Value | Meaning |
|---|---|
| positive | melody entropy changes more strongly than harmony entropy |
| negative | harmony entropy changes more strongly than melody entropy |
| near zero | melody and harmony change similarly |

In Mozart:

| Cadence | dH melody - dH harmony | 95% CI |
|---|---:|---:|
| PAC | 0.25 | [0.05, 0.44] |
| HC | 0.49 | [0.23, 0.73] |
| DC | -0.75 | [-1.59, 0.02] |
| EC | 0.50 | [0.15, 0.84] |

The contrast **DC vs EC** is significant:

```text
DC - EC = -1.25
95% CI [-2.17, -0.41]
FDR q = 0.018
```

This supports the interpretation that Mozart DC and EC differ not only in terminal IC, but also in their local entropy dynamics.

In Beethoven:

| Cadence | dH melody - dH harmony | 95% CI |
|---|---:|---:|
| PAC | 0.61 | [0.42, 0.80] |
| IAC | 0.61 | [0.29, 0.93] |
| HC | 0.14 | [-0.13, 0.41] |
| DC | 1.63 | [0.58, 2.72] |
| EC | 0.51 | [-0.04, 1.09] |

Beethoven DC shows a large positive gradient difference. Combined with its extremely high harmony IC, this suggests a special profile:

> The model has strong harmonic expectations, but the actual DC harmony violates them sharply.  
> In other words, Beethoven DC reflects a confident harmonic expectation being broken.

## 6. Standardized Melody-Harmony IC Space

Because raw melody IC and harmony IC are not necessarily on the same scale, we standardized each domain within each composer:

```text
M_z = z(melody IC)
H_z = z(harmony IC)
```

Then we plotted:

```text
x-axis = z(Harmony IC)
y-axis = z(Melody IC)
```

![Standardized IC space](/D:/music/output/idyom_domain_z_dominance/standardized_ic_space_piece_level_dc_ec.svg)

This visualization is the cleanest way to compare whether a cadence is melody- or harmony-dominant.

Piece-level mean positions:

| Composer | Cadence | z(Harmony IC) | z(Melody IC) |
|---|---|---:|---:|
| Mozart | DC | 1.30 | -0.13 |
| Mozart | EC | 0.73 | 0.88 |
| Beethoven | DC | 2.36 | -0.32 |
| Beethoven | EC | 0.64 | 0.69 |

Interpretation:

```text
DC moves rightward: harmony-domain surprise is high.
EC moves upward: melody-domain surprise is high.
Beethoven DC is the most extreme harmony-dominant case.
```

## 7. Domain Dominance Index

To directly test whether DC is more harmony-dominant than EC, we defined:

```text
dominance_index = H_z - M_z
```

Interpretation:

| Dominance index | Meaning |
|---|---|
| > 0 | harmony surprise is more prominent |
| < 0 | melody surprise is more prominent |
| around 0 | neither domain clearly dominates |

![Surprise dominance space](/D:/music/output/idyom_domain_z_dominance/surprise_dominance_space_piece_level_dc_ec.svg)

### Dominance Summary

| Composer | Cadence | Melody z | Harmony z | Dominance | 95% CI |
|---|---|---:|---:|---:|---:|
| Mozart | DC | -0.13 | 1.30 | 1.42 | [0.72, 2.19] |
| Mozart | EC | 0.88 | 0.73 | -0.15 | [-0.74, 0.42] |
| Beethoven | DC | -0.32 | 2.36 | 2.67 | [2.25, 3.09] |
| Beethoven | EC | 0.69 | 0.64 | -0.05 | [-0.79, 0.67] |

The key contrasts are:

| Composer | Contrast | Mean difference | 95% CI | FDR q |
|---|---|---:|---:|---:|
| Mozart | DC - EC | 1.58 | [0.63, 2.50] | 0.002 |
| Beethoven | DC - EC | 2.72 | [1.91, 3.61] | < 0.001 |

This directly supports the core claim:

> DC is significantly more harmony-dominant than EC in both Mozart and Beethoven.

The effect is larger in Beethoven, suggesting that Beethoven deceptive cadences create a more extreme harmonic violation than Mozart deceptive cadences.

## 8. Main Interpretive Conclusions

### Finding 1: EC is melodically surprising

In both composers, EC has high melody IC. This is especially clear in the melody-only IDyOM curves, where EC rises above the other cadence types around the cadence point.

Interpretation:

> EC is not simply a weak or failed cadence. It is a cadence whose expected melodic arrival is disrupted or displaced.

### Finding 2: DC is harmonically surprising

DC has the highest harmony IC in both composers. The effect is present in Mozart and extreme in Beethoven.

Interpretation:

> DC primarily violates harmonic expectation. The listener/model expects a conventional harmonic resolution, but receives a deceptive continuation.

### Finding 3: PAC is low surprise and relatively closure-like

PAC has low harmony IC and relatively low melody IC, especially in Mozart. This fits the theoretical role of PAC as the most conventional and stable closure type.

Interpretation:

> PAC behaves like a predictable closure schema in both melody and harmony.

### Finding 4: DC and EC separate cleanly in standardized domain space

The standardized IC space shows:

```text
DC: high z(Harmony IC), lower z(Melody IC)
EC: higher z(Melody IC), less harmony-dominant
```

This is important because it avoids comparing raw melody IC and harmony IC directly. After domain-wise normalization, the contrast remains strong.

### Finding 5: Beethoven intensifies the harmony-dominant DC profile

Beethoven DC has:

```text
z(Harmony IC) = 2.36
z(Melody IC) = -0.32
dominance_index = 2.67
```

This means Beethoven DC is not merely somewhat more harmonic than melodic. It is a highly domain-specific harmonic violation.

## 9. Recommended Paper Claim

A concise version suitable for the paper:

> Original IDyOM analyses show that cadence types differ not only in terminal information content, but also in the musical domain in which surprise is concentrated. Evaded cadences are associated with elevated melodic IC, whereas deceptive cadences are associated with elevated harmonic IC. After z-scoring melody and harmony IC within each domain, deceptive cadences are significantly more harmony-dominant than evaded cadences in both Mozart and Beethoven, with the effect especially strong in Beethoven. These results support a domain-specific account of cadential expectation: DC reflects harmonic expectation violation, while EC reflects melodic or phrase-level evasion.

## 10. Key Output Files

| File | Description |
|---|---|
| `/D:/music/output/idyom_ic_profiles_ci/melody_ic_profiles_mozart_beethoven_ci_ribbon.svg` | Pure melody IC curves with 95% CI bands |
| `/D:/music/output/idyom_ic_profiles_ci/harmony_ic_profiles_mozart_beethoven_ci_ribbon.svg` | Pure harmony IC curves with 95% CI bands |
| `/D:/music/output/idyom_domain_z_dominance/standardized_ic_space_piece_level_dc_ec.svg` | z(Harmony IC) x z(Melody IC) DC/EC space |
| `/D:/music/output/idyom_domain_z_dominance/surprise_dominance_space_piece_level_dc_ec.svg` | overall surprise x dominance space |
| `/D:/music/output/idyom_domain_z_dominance/DOMAIN_Z_DOMINANCE_REPORT.md` | dominance statistics |
| `/D:/music/output/idyom_pure_track_significance_mozart/IDYOM_PURE_TRACK_SIGNIFICANCE_REPORT.md` | Mozart significance tests |
| `/D:/music/output/idyom_pure_track_significance_beethoven/IDYOM_PURE_TRACK_SIGNIFICANCE_REPORT.md` | Beethoven significance tests |
