from __future__ import annotations

import math
import random
from statistics import mean, median, pstdev
from typing import Iterable, Sequence


def summarize(values: Iterable[float]) -> dict[str, float]:
    vals = [float(value) for value in values]
    if not vals:
        return {"n": 0, "mean": math.nan, "sd": math.nan, "median": math.nan}
    return {
        "n": len(vals),
        "mean": mean(vals),
        "sd": pstdev(vals) if len(vals) > 1 else 0.0,
        "median": median(vals),
    }


def lag1_autocorrelation(values: Sequence[float]) -> float:
    vals = [float(value) for value in values]
    if len(vals) < 3:
        return 0.0
    x = vals[:-1]
    y = vals[1:]
    mx = mean(x)
    my = mean(y)
    numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denominator = math.sqrt(
        sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)
    )
    return numerator / denominator if denominator else 0.0


def paired_sign_permutation_pvalue(
    differences: Sequence[float], seed: int = 13, permutations: int = 1000
) -> float:
    diffs = [float(diff) for diff in differences if not math.isnan(diff)]
    if not diffs:
        return math.nan
    observed = abs(mean(diffs))
    rng = random.Random(seed)
    extreme = 0
    for _ in range(permutations):
        sampled = [diff if rng.random() < 0.5 else -diff for diff in diffs]
        if abs(mean(sampled)) >= observed:
            extreme += 1
    return (extreme + 1) / (permutations + 1)


def auc_score(labels: Sequence[int], scores: Sequence[float]) -> float:
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return math.nan

    rank_sum = 0.0
    index = 0
    while index < len(pairs):
        end = index + 1
        while end < len(pairs) and pairs[end][0] == pairs[index][0]:
            end += 1
        avg_rank = (index + 1 + end) / 2
        rank_sum += avg_rank * sum(label for _, label in pairs[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)
