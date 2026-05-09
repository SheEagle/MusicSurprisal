import unittest

from music_surprisal.ngram import NGramModel, shuffled_sequences


class NGramModelTest(unittest.TestCase):
    def test_seen_context_is_more_predictable_than_unseen_token(self):
        model = NGramModel(order=2, alpha=0.1).fit([[60, 62, 64], [60, 62, 65]])
        self.assertGreater(model.probability(62, [60]), model.probability(65, [60]))

    def test_sequence_surprisal_matches_length(self):
        model = NGramModel(order=3).fit([[1, 2, 3, 4]])
        self.assertEqual(len(model.sequence_surprisal([1, 2, 3])), 3)

    def test_shuffled_sequences_preserve_inventory(self):
        sequences = [[1, 2, 3], [4, 5, 6]]
        shuffled = shuffled_sequences(sequences, seed=1)
        self.assertEqual([sorted(seq) for seq in shuffled], [sorted(seq) for seq in sequences])


if __name__ == "__main__":
    unittest.main()
