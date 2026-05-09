import tempfile
import unittest
from pathlib import Path

from music_surprisal.analysis import build_surprisal_rows, run_pipeline
from music_surprisal.data import read_events


class PipelineTest(unittest.TestCase):
    def test_demo_pipeline_writes_outputs(self):
        events = read_events(Path("examples") / "demo_events.csv")
        with tempfile.TemporaryDirectory() as tmp:
            paths = run_pipeline(events, tmp, permutations=20)
            for path in paths.values():
                self.assertTrue(Path(path).exists())

    def test_surprisal_rows_include_baselines(self):
        events = read_events(Path("examples") / "demo_events.csv")
        rows = build_surprisal_rows(events, order=2)
        self.assertTrue(rows)
        self.assertIn("surprisal_ngram", rows[0])
        self.assertIn("surprisal_unigram", rows[0])
        self.assertIn("surprisal_shuffled", rows[0])


if __name__ == "__main__":
    unittest.main()
