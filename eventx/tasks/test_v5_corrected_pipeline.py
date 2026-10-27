"""Synthetic-only regression suite for the V5 timing/stacking/offset repairs."""

from dataclasses import replace
import unittest

import numpy as np
from scipy.optimize import check_grad
from scipy.special import expit

from eventx.v5_corrected.offset import OffsetLogistic, smooth_objective
from eventx.v5_corrected.pipeline import Candidate, NestedOffsetTrainer, market_model
from eventx.v5_corrected.point_in_time import (
    Article, Decision, FeatureBatch, Metadata, PITSource, SemanticEncoder, metadata_at,
)
from eventx.v5_corrected.splits import Fold, HORIZON_US, MINUTE_US, RowIndex


def fixture():
    """No paths, sockets, environment credentials or real research inputs."""
    families = tuple("ABCDEFGH")
    decisions, metadata, articles, labels = [], [], [], []
    for f, family in enumerate(families):
        metadata.append(Metadata(family, "v1", 0, 0, None,
                                 "bitcoin price inflation", "crypto", True, 5000*MINUTE_US))
        for j in range(8):
            articles.append(Article(f"warm-{family}-{j}", j*MINUTE_US, j*MINUTE_US,
                                    j*MINUTE_US,
                                    f"bitcoin price inflation report {family.lower()} token{j} change",
                                    frozenset([family])))
        for day in range(10):
            start = 200 + day*120
            articles.append(Article(f"news-{family}-{day}", (start+5)*MINUTE_US,
                                    (start+5)*MINUTE_US, (start+5)*MINUTE_US,
                                    f"bitcoin price inflation report token{day} {family.lower()}",
                                    frozenset([family])))
            for j in range(4):
                time = (start + j*20)*MINUTE_US
                decisions.append(Decision(family, time, time+HORIZON_US, family, True,
                                          (float(j), float(day % 3), float(f % 2)), time, True))
                labels.append((day+j+f) % 2)
    source = PITSource(decisions, metadata, articles, 50*MINUTE_US,
                       {"components": 2, "min_df": 1, "max_df": 1.0},
                       association=lambda meta, text: "bitcoin" in text)

    def fold(name, day, endday, group):
        return Fold(name, (200+day*120)*MINUTE_US, (200+endday*120)*MINUTE_US,
                    frozenset(group))
    crossfit = [fold("early-ab", 2, 5, "AB"), fold("early-cd", 2, 5, "CD"),
                fold("early-ef", 2, 5, "EF")]
    tuning = [fold("tune-ef", 6, 8, "EF")]
    outer = fold("outer-gh", 8, 10, "GH")
    return source, np.array(labels), crossfit, tuning, outer


class ArraySource:
    """Fast synthetic feature factory for nesting tests; not a production adapter."""
    def __init__(self, index):
        self.index = index
        rng = np.random.default_rng(9)
        self.market = rng.normal(size=(len(index.decision), 3))
        self.residual = rng.normal(size=(len(index.decision), 2))
        self.exposed = np.arange(len(index.decision)) % 3 == 0

    def fit(self, train):
        source = self

        class Fitted:
            provenance = {"synthetic": True, "fit_ids": np.asarray(train).tolist()}

            def transform(self, ids):
                return FeatureBatch(source.market[ids], source.residual[ids], source.exposed[ids])

        return Fitted()


class OffsetTests(unittest.TestCase):
    def test_gradient(self):
        rng = np.random.default_rng(2)
        x = np.column_stack([rng.normal(size=(80, 3)), np.ones(80)])
        y, offset = rng.integers(0, 2, 80), rng.normal(size=80)
        args = (x, y, offset, .13)
        error = check_grad(lambda b: smooth_objective(b, *args)[0],
                           lambda b: smooth_objective(b, *args)[1], np.ones(4)*.1)
        self.assertLess(error, 1e-6)

    def test_calibrated_offset_stays_zero(self):
        model = OffsetLogistic().fit(np.ones((100, 1)), np.arange(100) % 5 == 0,
                                      np.full(100, .2), np.ones(100, bool))
        np.testing.assert_allclose(model.coef_, 0, atol=1e-7)
        self.assertLessEqual(model.kkt_residual_, model.tol)

    def test_known_correction_recovery(self):
        rng = np.random.default_rng(3)
        x = rng.normal(size=(12000, 1))
        offsets = rng.normal(-1, .4, len(x))
        y = rng.random(len(x)) < expit(offsets + .6*x[:, 0])
        model = OffsetLogistic(l2=.001).fit(x, y, expit(offsets), np.ones(len(x), bool))
        raw_slope = model.coef_[0] / model.scaler_.scale_[0]
        self.assertAlmostEqual(raw_slope, .6, delta=.06)

    def test_exposed_scaling_and_exact_equality(self):
        x = np.array([[0.], [1.], [2.], [3.], [1e9], [-1e9]])
        e = np.array([1, 1, 1, 1, 0, 0], bool)
        p0 = np.array([.2, .3, .4, .5, .123456789, .876543211])
        model = OffsetLogistic(l1=.02).fit(x, [0, 1, 0, 1, 1, 0], p0, e)
        self.assertEqual(model.scaler_.mean_[0], 1.5)
        np.testing.assert_array_equal(model.predict(x, p0, e)[~e], p0[~e])
        np.testing.assert_array_equal(model.predict(x, p0, e, 0), p0)

    def test_l1_suppression_no_exposure_and_failures(self):
        x = np.arange(100).reshape(-1, 1)
        y, p = np.arange(100) % 2, np.full(100, .5)
        model = OffsetLogistic(l1=10).fit(x, y, p, np.ones(100, bool))
        self.assertEqual(model.coef_[0], 0)
        empty = OffsetLogistic().fit(x, y, p, np.zeros(100, bool))
        np.testing.assert_array_equal(empty.predict(x, p, np.ones(100, bool)), p)
        with self.assertRaises(ValueError):
            model.fit(x, np.ones(100), p, np.ones(100, bool))
        with self.assertRaises(RuntimeError):
            OffsetLogistic(max_iter=1, tol=1e-14).fit(x, y, p, np.ones(100, bool))
        with self.assertRaises(ValueError):
            model.predict(x, np.ones(100), np.ones(100, bool))


class PointInTimeTests(unittest.TestCase):
    def setUp(self):
        self.source, _, _, _, _ = fixture()

    def test_metadata_receipt_and_revisions(self):
        first = Metadata("x", "v1", 20, 0, None, "q", "crypto", True, 100)
        later = replace(first, version="v2", available=80, scheduled_terminal=200)
        self.assertIsNone(metadata_at([first, later], "x", 19))
        self.assertEqual(metadata_at([first, later], "x", 30).scheduled_terminal, 100)
        self.assertEqual(metadata_at([first, later], "x", 80).scheduled_terminal, 200)
        closed = replace(later, version="v3", available=90, is_open=False)
        self.assertTrue(metadata_at([first, later, closed], "x", 89).is_open)
        self.assertFalse(metadata_at([first, later, closed], "x", 90).is_open)

    def test_unknown_terminal_is_not_future_backfilled(self):
        s = self.source
        original = s.metadata[0]
        unknown = replace(original, scheduled_terminal=None)
        future = replace(original, version="later", available=10000*MINUTE_US)
        s.metadata = (unknown, *s.metadata[1:], future)
        fitted = s.fit(np.arange(40))
        result = fitted.transform(np.array([0])).market[0]
        np.testing.assert_array_equal(result[-2:], [0, 1])

    def test_missing_metadata_coverage_and_future_market_input_fail(self):
        s = self.source
        for bad in [replace(s.decisions[0], market_available=s.decisions[0].time+1),
                    replace(s.decisions[0], coverage_complete=False),
                    replace(s.decisions[0], family_verified=False)]:
            with self.assertRaises(ValueError):
                PITSource([bad], s.metadata, s.articles, s.cutoff)
        with self.assertRaises(ValueError):
            PITSource([s.decisions[0]], [], s.articles, s.cutoff)

    def test_semantic_fit_time_and_family_scope(self):
        s = self.source
        future = Article("future", 999999*MINUTE_US, 0, 0, "secretfuturetoken", frozenset("A"))
        encoder = SemanticEncoder(s.cutoff, 2, 1, 1.0).fit([*s.articles, future], frozenset("A"))
        self.assertTrue(all(identity.startswith("warm-A") for identity in encoder.fit_ids))
        self.assertNotIn("secretfuturetoken", encoder.vectorizer.vocabulary_)
        with self.assertRaises(ValueError):
            encoder.transform(["bitcoin"], s.cutoff-1)

    def test_future_append_invariance_and_news_window(self):
        s = self.source
        ids = np.arange(8)
        fitted = s.fit(np.arange(40))
        before = fitted.transform(ids)
        later = replace(s.metadata[0], version="future", available=10000*MINUTE_US,
                        question="future question")
        article = Article("future", 10000*MINUTE_US, 0, 0, "future news", frozenset("A"))
        augmented = PITSource(s.decisions, [*s.metadata, later], [*s.articles, article],
                              s.cutoff, s.semantic_options, s.association)
        after = augmented.fit(np.arange(40)).transform(ids)
        np.testing.assert_array_equal(before.market, after.market)
        np.testing.assert_array_equal(before.residual, after.residual)
        # At 200 no article in (170,200]; at 220 article205; at240 it has expired.
        np.testing.assert_array_equal(before.exposed[:4], [False, True, False, False])

    def test_article_revision_never_rewrites_earlier_text(self):
        s = self.source
        old = s.articles[0]
        revised = replace(old, content_available=10000*MINUTE_US, text="revised future text")
        new = PITSource(s.decisions, s.metadata, [*s.articles, revised], s.cutoff,
                        s.semantic_options, s.association)
        self.assertEqual(new.articles[0].text, old.text)

    def test_exact_news_boundary_and_late_content(self):
        s = self.source
        d = s.decisions[0]
        articles = [a for a in s.articles if a.available < s.cutoff]
        articles += [Article("left", d.time-HORIZON_US, 0, 0, "bitcoin old", frozenset("A")),
                     Article("right", d.time, 0, 0, "bitcoin new", frozenset("A")),
                     Article("backfill", d.time-1, 0, d.time+1, "bitcoin late", frozenset("A"))]
        new = PITSource(s.decisions, s.metadata, articles, s.cutoff,
                        s.semantic_options, s.association)
        fitted = new.fit(np.arange(40))
        raw_market, gate, raw_news = fitted._raw([0])
        self.assertTrue(gate[0])
        self.assertEqual(raw_news[0, 3], 1)  # only right boundary is included
        self.assertEqual(raw_news[0, 2], 0)

    def test_no_association_before_market_metadata_exists(self):
        s = self.source
        # The article at205 predates the first market snapshot at210. A220 is
        # eligible but this news cannot acquire a retrospectively inferred link.
        metadata = [replace(m, available=210*MINUTE_US) if m.market == "A" else m
                    for m in s.metadata]
        decisions = [s.decisions[1], *s.decisions[40:80]]
        new = PITSource(decisions, metadata, s.articles, s.cutoff,
                        s.semantic_options, s.association)
        self.assertFalse(new.fit(np.arange(len(decisions))).transform([0]).exposed[0])

    def test_invalid_timestamps_and_family_switch_fail(self):
        s = self.source
        with self.assertRaises(ValueError):
            replace(s.articles[0], content_available=None)
        with self.assertRaises(ValueError):
            PITSource([s.decisions[0], replace(s.decisions[1], family="other")],
                      s.metadata, s.articles, s.cutoff)

    def test_count_cap_and_semantics_do_not_use_validation_rows(self):
        s = self.source
        fitted = s.fit(np.array([0, 2, 3]))  # all no-news rows
        self.assertEqual(fitted.count_cap, 0)
        self.assertTrue(fitted.transform([1]).exposed[0])
        self.assertEqual(fitted.transform([1]).residual[0, -2], 0)  # capped count


class CrossFitTests(unittest.TestCase):
    def test_purge_and_family_boundary(self):
        t = np.array([0, 1, 29, 30, 60, 61], dtype=np.int64)*MINUTE_US
        index = RowIndex(t, t+HORIZON_US, np.array(["A", "B", "A", "A", "B", "B"]),
                         np.ones(6, bool))
        train, valid = index.split(np.arange(6), Fold("f", 60*MINUTE_US,
                                  120*MINUTE_US, frozenset("B")))
        np.testing.assert_array_equal(train, [0, 2])  # at30+30 touches60: purged
        np.testing.assert_array_equal(valid, [4, 5])

    def test_nested_isolation_and_outer_label_perturbation(self):
        raw, y, crossfit, tuning, outer = fixture()
        source = ArraySource(raw.index)
        trainer = NestedOffsetTrainer(source, y, market_model, crossfit)
        model, valid, tuning_report = trainer.fit_outer(outer, tuning,
                                                       [Candidate(0, .1, 0), Candidate(.01, .1, 1)])
        self.assertFalse(tuning_report["outer_labels_inspected"])
        for entry in trainer.ledger:
            if "train_families" in entry:
                self.assertFalse(set(entry["train_families"]) & set("GH"))
                if entry["valid_ids"]:
                    self.assertFalse(set(entry["train_families"]) & set(entry["valid_families"]))
                    self.assertLess(entry["max_train_label_end"],
                                    raw.index.decision[entry["valid_ids"]].min())
                if entry["stage"].startswith("inner/"):
                    self.assertFalse(set(entry["train_families"]) & set("EF"))
        changed = y.copy()
        changed[np.isin(raw.index.family, list("GH"))] ^= 1
        other = NestedOffsetTrainer(source, changed, market_model, crossfit)
        other_model, other_valid, other_report = other.fit_outer(
            outer, tuning, [Candidate(0, .1, 0), Candidate(.01, .1, 1)])
        np.testing.assert_array_equal(valid, other_valid)
        np.testing.assert_array_equal(model.predict(valid)[1], other_model.predict(valid)[1])
        self.assertEqual(tuning_report, other_report)
        self.assertGreater(len(model.excluded_warmup_ids), 0)
        # Residual offsets exactly equal individually recorded, held-family base OOF.
        ids, p0 = trainer.crossfit(np.array(trainer.ledger[-1]["train_ids"]), "check")
        np.testing.assert_array_equal(ids, model.oof_ids)
        np.testing.assert_array_equal(p0, model.oof_p0)

    def test_duplicate_oof_folds_fail(self):
        raw, y, crossfit, _, outer = fixture()
        trainer = NestedOffsetTrainer(ArraySource(raw.index), y, market_model,
                                       [crossfit[0], crossfit[0]])
        parent, _ = raw.index.split(np.arange(len(y)), outer)
        with self.assertRaisesRegex(ValueError, "Overlapping OOF"):
            trainer.crossfit(parent, "bad")

    def test_validation_future_text_does_not_enter_inner_semantic_fit(self):
        source, y, crossfit, tuning, outer = fixture()
        trainer = NestedOffsetTrainer(source, y, market_model, crossfit)
        trainer.fit_outer(outer, tuning, [Candidate(.01, .1, .5)])
        for entry in trainer.ledger:
            if "feature_provenance" not in entry:
                continue
            permitted = set(entry["train_families"])
            ids = entry["feature_provenance"]["semantic_article_ids"]
            self.assertTrue(all(identity.split("-")[1] in permitted for identity in ids))

    def test_raw_pit_to_nested_offset_integration(self):
        source, y, crossfit, tuning, outer = fixture()
        trainer = NestedOffsetTrainer(source, y, market_model, crossfit)
        stack, valid, _ = trainer.fit_outer(outer, tuning, [Candidate(.01, .1, .5)])
        p0, result = stack.predict(valid)
        e = stack.features.transform(valid).exposed
        np.testing.assert_array_equal(result[~e], p0[~e])
        self.assertTrue(np.isfinite(result).all())
        self.assertEqual(stack.residual.status_, "converged")
        self.assertTrue(all(identity.startswith(tuple(f"warm-{f}" for f in "ABCDEF"))
                            for identity in stack.features.encoder.fit_ids))

    def test_shallow_tree_remains_available_without_promotion(self):
        tree = market_model("shallow_tree")
        self.assertEqual(tree.max_depth, 3)
        self.assertFalse(tree.early_stopping)


if __name__ == "__main__":
    unittest.main()
