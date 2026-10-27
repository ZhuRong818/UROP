"""Supplementary variable-content integration; all inputs/labels are synthetic."""

import unittest
import numpy as np

from eventx.tasks.test_v5_experiment_v1 import integrated_fixture
from eventx.v5_corrected.experiment_v1 import ExperimentTrainer, ARMS


class VariableContentTests(unittest.TestCase):
    def test_content_change_only_changes_news_expert(self):
        source, y, base, oof, _, outer = integrated_fixture()
        rng = np.random.default_rng(1024)
        e = source.exposed
        source.news[e, 2] = rng.uniform(0, 29, e.sum())
        source.news[e, 3] = np.log1p(rng.integers(1, 6, e.sum()))
        source.news[e, 0] = .1+.8*y[e]
        source.news[e, 1] = .8*source.news[e, 0]
        parent, valid = source.index.split(np.arange(len(y)), outer)
        specs = {a: (.01, 0., 1.) for a in ARMS}
        original = ExperimentTrainer(source, y, base, oof).fit_models(parent, specs)
        before = original.predict(valid)
        # Explicit strong null-content intervention; timing/market inputs unchanged.
        source.news[e, 0:2] = 0
        altered = ExperimentTrainer(source, y, base, oof).fit_models(parent, specs)
        after = altered.predict(valid)
        for arm in ("nonlinear", "context", "timing", "timing_matched"):
            np.testing.assert_array_equal(before[arm], after[arm])
        self.assertGreater(np.max(np.abs(before["news"]-after["news"])), .01)


if __name__ == "__main__":
    unittest.main()
