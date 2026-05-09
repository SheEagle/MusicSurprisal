from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Hashable, Iterable, Sequence

Token = Hashable
SequenceLike = Sequence[Token]

START = "<s>"
UNK = "<UNK>"


@dataclass
class NGramModel:
    """Additive-smoothed n-gram model with recursive backoff."""

    order: int = 3
    alpha: float = 0.1
    vocab: set[Token] = field(default_factory=set)
    counts: dict[tuple[Token, ...], Counter[Token]] = field(
        default_factory=lambda: defaultdict(Counter)
    )
    context_totals: Counter[tuple[Token, ...]] = field(default_factory=Counter)

    def __post_init__(self) -> None:
        if self.order < 1:
            raise ValueError("order must be >= 1")
        if self.alpha <= 0:
            raise ValueError("alpha must be > 0")

    def fit(self, sequences: Iterable[SequenceLike]) -> "NGramModel":
        prepared = [list(seq) for seq in sequences if len(seq) > 0]
        self.vocab = {token for seq in prepared for token in seq}
        self.vocab.add(UNK)
        self.counts = defaultdict(Counter)
        self.context_totals = Counter()

        for seq in prepared:
            padded = [START] * (self.order - 1) + seq
            for i in range(self.order - 1, len(padded)):
                token = padded[i]
                history = padded[max(0, i - self.order + 1) : i]
                for context_len in range(0, min(self.order - 1, len(history)) + 1):
                    context = tuple(history[-context_len:]) if context_len else ()
                    self.counts[context][token] += 1
                    self.context_totals[context] += 1
        return self

    def probability(self, token: Token, context: SequenceLike = ()) -> float:
        if not self.vocab:
            raise ValueError("model must be fit before scoring")

        mapped = token if token in self.vocab else UNK
        context_tuple = tuple(context)[-(self.order - 1) :] if self.order > 1 else ()

        while context_tuple and self.context_totals[context_tuple] == 0:
            context_tuple = context_tuple[1:]

        vocab_size = len(self.vocab)
        total = self.context_totals[context_tuple]
        count = self.counts[context_tuple][mapped]
        return (count + self.alpha) / (total + self.alpha * vocab_size)

    def surprisal(self, token: Token, context: SequenceLike = ()) -> float:
        return -math.log2(self.probability(token, context))

    def sequence_surprisal(self, sequence: SequenceLike) -> list[float]:
        values: list[float] = []
        history: list[Token] = [START] * (self.order - 1)
        for token in sequence:
            values.append(self.surprisal(token, history))
            history.append(token)
        return values


def shuffled_sequences(
    sequences: Iterable[SequenceLike], seed: int = 13
) -> list[list[Token]]:
    """Return per-piece shuffled copies, preserving each piece's token inventory."""

    rng = random.Random(seed)
    shuffled: list[list[Token]] = []
    for seq in sequences:
        copy = list(seq)
        rng.shuffle(copy)
        if copy:
            shuffled.append(copy)
    return shuffled
