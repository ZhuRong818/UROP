"""Synthetic-only revision tests; no research dataset or protected outcome access."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from eventx.tasks.test_v5_experiment_v1 import integrated_fixture
from eventx.v5_corrected.experiment_v1 import ExperimentTrainer
from eventx.v5_corrected.final_fit_v1_1 import fit_final
from eventx.v5_corrected.rehearsal_v1_1 import REQUIRED_EVIDENCE, synthetic_once, verify_evidence
from eventx.v5_corrected.uncertainty_v1_1 import (
    moving_block_draws, wilson, interpret_interval, news_decision,
)


class RevisionTests(unittest.TestCase):
    def test_paired_deterministic_draws(self):
        f, d = np.repeat(np.arange(3), 35), np.tile(np.arange(35), 3)
        x = np.arange(len(f))/1000
        a = moving_block_draws(np.column_stack([x, x+.25]), f, d,
                               block_days=7, replicates=129)
        b = moving_block_draws(np.column_stack([x, x+.25]), f, d,
                               block_days=7, replicates=129)
        np.testing.assert_array_equal(a, b)
        np.testing.assert_allclose(a[:, 1]-a[:, 0], .25)

    def test_calendar_gaps_and_short_support_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Missing calendar'):
            moving_block_draws([1, 2, 3], [0, 0, 0], [0, 1, 3], block_days=1)
        with self.assertRaisesRegex(ValueError, 'two block'):
            moving_block_draws(np.ones(20), np.zeros(20), np.arange(20), block_days=14)

    def test_constant_and_single_family(self):
        draws = moving_block_draws(np.ones(35), np.zeros(35), np.arange(35),
                                   block_days=14, replicates=50)
        np.testing.assert_array_equal(draws, np.ones((50, 1)))

    def test_synchronous_common_shock_not_divided_by_family_count(self):
        signal = np.sin(np.arange(35)/5)
        one = moving_block_draws(signal, np.zeros(35), np.arange(35), block_days=7,
                                 replicates=500, resample_families=False)
        many = moving_block_draws(np.tile(signal, 30), np.repeat(np.arange(30), 35),
                                  np.tile(np.arange(35), 30), block_days=7,
                                  replicates=500, resample_families=False)
        # RNG consumes family draws differently, so compare scale rather than values.
        self.assertGreater(many.std()/one.std(), .8)
        self.assertLess(many.std()/one.std(), 1.2)

    def test_invalid_uncertainty_input(self):
        for values in ([float('nan')]*35, [float('inf')]*35):
            with self.assertRaises(ValueError):
                moving_block_draws(values, np.zeros(35), np.arange(35), block_days=7)

    def test_interval_interpretation(self):
        self.assertEqual(interpret_interval(-.004, -.001), 'evidence_of_harm')
        self.assertEqual(interpret_interval(-.001, .0008), 'useful_gain_excluded')
        self.assertEqual(interpret_interval(-.001, .002), 'inconclusive')
        self.assertIn('positive_effect', interpret_interval(.0001, .002))
        self.assertGreater(wilson(100, 100)[0], .96)
        self.assertGreater(wilson(0, 100)[1], 0)

    def test_replication_is_separate(self):
        means = [-.001, .002, .001, .0001]
        bounds = [[-.002, .001, .0001, -.0001], [0., .003, .002, .0003]]
        result = news_decision(means, bounds, certified=True)
        self.assertTrue(result['promote_news'])
        self.assertFalse(result['market_replication_passed'])
        self.assertEqual(result['subgroup_assessment'], 'not_assessable')
        result = news_decision(means, bounds, certified=True, subgroup_lower=[-.002])
        self.assertFalse(result['promote_news'])

    def test_uncertified_policy_does_not_touch_metrics(self):
        class Sealed:
            def __array__(self, *args, **kwargs):
                raise AssertionError('Metrics accessed')
        self.assertEqual(news_decision(Sealed(), Sealed())['status'], 'incomplete')

    def fixture_evidence(self, root):
        (root/'SYNTHETIC_ONLY').write_text('Synthetic fixture only\n')
        (root/'evidence.json').write_text('{"synthetic": true}\n')
        digest = hashlib.sha256((root/'evidence.json').read_bytes()).hexdigest()
        return {role: {'path': 'evidence.json', 'sha256': digest} for role in REQUIRED_EVIDENCE}

    def test_receipt_precedes_labels_and_rerun_refused(self):
        with tempfile.TemporaryDirectory(prefix='eventx-v5-synthetic-') as temp:
            root = Path(temp)
            evidence = self.fixture_evidence(root)
            def load():
                self.assertTrue((root/'attempt.json').exists())
                return [0, 1]
            args = dict(synthetic=True, approved=True, evidence=evidence,
                        load_labels=load, evaluate=lambda y: {'synthetic_rows': len(y)})
            self.assertEqual(synthetic_once(root, **args), {'synthetic_rows': 2})
            with self.assertRaises(FileExistsError):
                synthetic_once(root, **args)

    def test_failed_attempt_consumes_scope(self):
        with tempfile.TemporaryDirectory(prefix='eventx-v5-synthetic-') as temp:
            root = Path(temp)
            evidence = self.fixture_evidence(root)
            def fail(_):
                raise RuntimeError('Synthetic injected crash')
            args = dict(synthetic=True, approved=True, evidence=evidence,
                        load_labels=lambda: [1], evaluate=fail)
            with self.assertRaises(RuntimeError):
                synthetic_once(root, **args)
            self.assertEqual(json.loads((root/'failure.json').read_text())['error_type'], 'RuntimeError')
            with self.assertRaises(FileExistsError):
                synthetic_once(root, **args)

    def test_admission_hash_and_real_mode_refusal(self):
        with tempfile.TemporaryDirectory(prefix='eventx-v5-synthetic-') as temp:
            root = Path(temp)
            evidence = self.fixture_evidence(root)
            args = dict(evidence=evidence, approved=True,
                        load_labels=lambda: self.fail('Labels accessed'), evaluate=lambda _: {})
            with self.assertRaises(ValueError):
                synthetic_once(root, synthetic=False, **args)
            (root/'evidence.json').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                synthetic_once(root, synthetic=True, **args)
            self.assertFalse((root/'attempt.json').exists())
            with self.assertRaises(ValueError):
                verify_evidence(root, {})

    def test_final_training_never_reads_confirmation_families(self):
        source, labels, base, oof, tuning, confirmation = integrated_fixture()
        held = np.isin(source.index.family, list(confirmation.families))
        masked = labels.astype(float)
        masked[held] = np.nan
        trainer = ExperimentTrainer(source, masked, base, oof)
        final, ids = fit_final(trainer, confirmation, tuning)
        predictions = final.predict(ids)
        self.assertEqual(set(predictions), {'linear', 'nonlinear', 'context', 'timing', 'timing_matched', 'news'})
        self.assertFalse(held[final.training_ids].any())
        for record in trainer.ledger:
            if record['stage'] == 'labels_accessed':
                self.assertFalse(held[record['ids']].any())
        self.assertTrue(set(final.residual_bundle.oof_ids).issubset(final.training_ids))
        for arm in ('context', 'timing', 'timing_matched', 'news'):
            np.testing.assert_array_equal(predictions[arm][~source.exposed[ids]],
                                          predictions['nonlinear'][~source.exposed[ids]])


if __name__ == '__main__':
    unittest.main()
