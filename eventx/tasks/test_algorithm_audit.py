"""Synthetic regression checks; these tests never read research data."""
import unittest
import numpy as np
from scipy.optimize import check_grad
from eventx.tasks.audit_v5_algorithms import (
    recent_news, split_masks, offset_objective, offset_sanity, START_US, MINUTE_US,
    OOF_DTYPE, EVENT_DTYPE, matrix_for,
)


class AlgorithmAuditTests(unittest.TestCase):
    def test_half_open_window_and_future_invariance(self):
        rows = np.zeros(3, dtype=OOF_DTYPE)
        rows['minute'] = [0, 30, 31]
        events = np.zeros(3, dtype=EVENT_DTYPE)
        events['timestamp_us'] = START_US + np.array([0, 30, 50]) * MINUTE_US
        events['relevance'] = [1, .5, 1]
        events['novelty'] = 1
        got = recent_news(rows, events)
        np.testing.assert_array_equal(got[:, 1], [1, 1, 1])
        np.testing.assert_array_equal(got[:, 2], [0, 0, 1])
        np.testing.assert_array_equal(got, recent_news(rows, events[:2]))
        rows['market'] = 1
        self.assertFalse(recent_news(rows, events).any())

    def test_purge_excludes_boundary_label_overlap(self):
        rows = np.zeros(5, dtype=OOF_DTYPE)
        rows['fold'] = [1, 2, 2, 2, 3]
        rows['minute'] = [11*1440, 33*1440-31, 33*1440-30, 33*1440-5, 33*1440]
        _, _, outer, val = split_masks(rows, 3)
        np.testing.assert_array_equal(outer, [True, True, False, False, False])
        self.assertTrue(val[-1])

    def test_offset_gradient_and_calibrated_baseline(self):
        rng = np.random.default_rng(7)
        x = rng.normal(size=(50, 3))
        y = rng.integers(0, 2, 50)
        offsets = rng.normal(size=50)
        args = (x, y, offsets, .1)
        error = check_grad(lambda b: offset_objective(b, *args)[0],
                           lambda b: offset_objective(b, *args)[1], np.zeros(3))
        self.assertLess(error, 1e-6)
        got = offset_sanity()
        self.assertAlmostEqual(got['true_offset_correction'], 0)
        self.assertGreater(abs(got['standalone_minus_baseline_correction']), .1)

    def test_count_cap_uses_training_only(self):
        market = np.zeros((3, 15))
        news = np.zeros((3, 5))
        news[:, 1] = [1, 2, 100000]
        x, meta = matrix_for(market, news, 'timing', np.array([0, 1]))
        self.assertLess(meta['train_only_article_count_cap'], 2)
        self.assertLess(x[2, 16], np.log(3))


if __name__ == '__main__':
    unittest.main()
