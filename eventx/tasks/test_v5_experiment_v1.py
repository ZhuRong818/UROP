"""Synthetic validation only; no network, warehouse or outcome files."""

from dataclasses import replace
import unittest

import numpy as np

from eventx.features.v5_market import MARKET_FEATURE_NAMES
from eventx.tasks.test_v5_corrected_pipeline import fixture
from eventx.v5_corrected.experiment_v1 import (
    Batch, ExperimentTrainer, NamedPITSource, GRID, family_groups, crossed_folds,
)
from eventx.v5_corrected.point_in_time import PITSource
from eventx.v5_corrected.splits import Fold, MINUTE_US
from eventx.v5_corrected.evaluation_v1 import bootstrap, evaluate


class SyntheticSource:
    def __init__(self, index):
        self.index = index
        rng = np.random.default_rng(912)
        self.market = rng.normal(size=(len(index.family), 15))
        self.market[:, 12] = 2
        self.market[:, 13] = 0
        self.market[:, 14] = 5
        self.exposed = np.arange(len(index.family)) % 3 == 0
        self.news = np.zeros((len(index.family), 5))
        self.news[self.exposed] = [.8, .6, 5, 1, 1.6]

    def fit(self, train):
        source = self

        class Features:
            provenance = {"synthetic": True, "fit_ids": np.asarray(train).tolist()}

            def transform(self, ids):
                return Batch(source.market[ids], source.news[ids], source.exposed[ids])

        return Features()


def integrated_fixture():
    source, labels, _, tuning, outer = fixture()
    families = "ABCDEFGH"
    def folds(prefix, start, end):
        return [Fold(prefix+f, (200+start*120)*MINUTE_US,
                     (200+end*120)*MINUTE_US, frozenset([f])) for f in families]
    return SyntheticSource(source.index), labels, folds("base", 1, 2), folds("oof", 3, 5), tuning, outer


class IntegratedTests(unittest.TestCase):
    def test_grid_and_folds(self):
        self.assertEqual(len(GRID), 24)
        self.assertEqual(GRID[0], (1., .5, 0.))
        families = [str(i) for i in range(31)]
        self.assertEqual(family_groups(families), family_groups(families[::-1]))
        f = crossed_folds(families, [(i*10, (i+1)*10) for i in range(5)])
        self.assertEqual(len(f), 25)
        self.assertEqual(set.union(*(set(x.families) for x in f[:5])), set(families))

    def test_named_raw_adapter(self):
        s, _, _, _, _ = fixture()
        names = tuple(n for n in MARKET_FEATURE_NAMES if n not in
                      {"log1p_minutes_to_scheduled_terminal", "terminal_unknown"})
        decisions = [replace(d, market_values=tuple(range(13))) for d in s.decisions]
        raw = PITSource(decisions, s.metadata, s.articles, s.cutoff, s.semantic_options, s.association)
        fitted = NamedPITSource(raw, names).fit(np.arange(40))
        batch = fitted.transform(np.array([0, 1, 2]))
        self.assertEqual(batch.market.shape, (3, 15))
        self.assertEqual(batch.market[0, 14], 12)  # price age, not unknown-terminal flag
        self.assertEqual(batch.market[0, 13], 0)
        self.assertEqual(batch.matrices(np.full(3, .2))["news"].shape, (3, 22))

    def test_nested_base_selection_outer_label_isolation(self):
        source, y, base, oof, tuning, outer = integrated_fixture()
        held = np.isin(source.index.family, list("GH"))
        masked = y.astype(float)
        masked[held] = np.nan  # even validation of these values would fail
        trainer = ExperimentTrainer(source, masked, base, oof)
        bundle, valid, p, selection = trainer.fit_outer(outer, tuning)
        self.assertEqual(set(p), {"linear", "nonlinear", "context", "timing", "timing_matched", "news"})
        self.assertFalse(selection["outer_labels_read"])
        for record in trainer.ledger:
            if record["stage"] == "labels_accessed":
                self.assertFalse(held[record["ids"]].any())
            elif record["stage"] == "split":
                train, v = record["train"], record["valid"]
                self.assertTrue(set(train).issubset(record["parent"]))
                self.assertTrue(set(v).issubset(record["parent"]))
                self.assertFalse(set(source.index.family[train]) & set(source.index.family[v]))
                self.assertLess(source.index.label_end[train].max(), source.index.decision[v].min())
        for arm in ("context", "timing", "timing_matched", "news"):
            np.testing.assert_array_equal(p[arm][~source.exposed[valid]], p["nonlinear"][~source.exposed[valid]])
        self.assertGreater(len(bundle.oof_ids), 0)
        self.assertGreater(len(bundle.diagnostics["excluded_no_oof_ids"]), 0)
        # A new trainer has no cached fits; arbitrary held labels cannot alter predictions.
        changed = y.copy()
        changed[held] ^= 1
        _, v2, p2, s2 = ExperimentTrainer(source, changed, base, oof).fit_outer(outer, tuning)
        np.testing.assert_array_equal(valid, v2)
        self.assertEqual(selection, s2)
        for arm in p:
            np.testing.assert_array_equal(p[arm], p2[arm])


class EvaluationTests(unittest.TestCase):
    def test_source_gate_precedes_label_read(self):
        class Sealed:
            def __array__(self, *args, **kwargs):
                raise AssertionError("Labels opened")
        result = evaluate(Sealed(), {}, [], [], [], [], {})
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["labels_accessed"])

    def test_paired_draws_and_constant_effect(self):
        family = np.repeat(np.arange(5), 6)
        day = np.tile(np.arange(6), 5)
        effect = np.arange(30)/100
        samples = bootstrap(np.column_stack([effect, 2*effect, np.full(30, .001)]),
                            family, day, day//3, replicates=100)["all"]
        np.testing.assert_allclose(samples[:, 1], 2*samples[:, 0])
        np.testing.assert_allclose(samples[:, 2], .001)
        repeat = bootstrap(np.column_stack([effect, 2*effect, np.full(30, .001)]),
                           family, day, day//3, replicates=100)["all"]
        np.testing.assert_array_equal(samples, repeat)

    def test_uncertainty_fails_on_empty_replication(self):
        with self.assertRaisesRegex(ValueError, "Empty-weight"):
            bootstrap([1., 2.], ["a", "b"], [1, 2], [0, 0],
                      masks={"sparse": np.array([True, False])}, replicates=100)

    def test_null_news_hard_stop_and_undefined_secondary_ap(self):
        family, day = np.repeat(np.arange(30), 35), np.tile(np.arange(35), 30)
        n = len(day)
        predictions = {a: np.full(n, .2) for a in
                       ["linear", "nonlinear", "context", "timing", "timing_matched", "news"]}
        result = evaluate(np.zeros(n), predictions, family, day, day//7, np.ones(n, bool), {},
                          source_gate_passed=True, software_gate_passed=True, replicates=100)
        self.assertEqual(result["status"], "negative_stop_news_branch")
        self.assertFalse(result["promote_news"])
        self.assertIsNone(result["metrics"]["news"]["ap"])
        self.assertFalse(result["gates"]["content_attribution"])


if __name__ == "__main__":
    unittest.main()
