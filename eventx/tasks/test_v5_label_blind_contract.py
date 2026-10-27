"""Synthetic only: family triage and matched timing/content matrix invariants."""

import unittest
import numpy as np

from eventx.features.v5_market import MARKET_FEATURE_NAMES
from eventx.tasks.review_v5_families_label_blind import review_group
from eventx.v5_corrected.matched_controls_v1 import matched_matrices


class LabelBlindContractTests(unittest.TestCase):
    def build(self, **changes):
        args = dict(market=np.arange(45).reshape(3, 15), names=MARKET_FEATURE_NAMES,
                    p0=[.2, .4, .6], exposed=np.array([True, False, True]),
                    age_minutes=[4, 0, 20], capped_log_count=[1, 0, 2],
                    qmax=[.8, 0, .5], qlast=[.6, 0, .1])
        args.update(changes)
        return matched_matrices(**args)

    def test_primary_width_and_shared_inputs(self):
        m = self.build()
        self.assertEqual(m["news"].shape, (3, 22))
        self.assertEqual(m["timing_matched"].shape, (3, 22))
        np.testing.assert_array_equal(m["news"][:, :19], m["timing_matched"][:, :19])

    def test_content_cannot_change_control(self):
        before, after = self.build(), self.build(qmax=[.9, 0, .9], qlast=[.7, 0, .7])
        for arm in ["context", "timing", "timing_matched"]:
            np.testing.assert_array_equal(before[arm], after[arm])
        self.assertFalse(np.array_equal(before["news"], after["news"]))

    def test_named_column_reordering(self):
        canonical = self.build()
        reverse = self.build(market=np.arange(45).reshape(3, 15)[:, ::-1],
                             names=MARKET_FEATURE_NAMES[::-1])
        np.testing.assert_array_equal(canonical["news"], reverse["news"])

    def test_bad_inputs_fail(self):
        for change in [dict(age_minutes=[30, 0, 20]), dict(qmax=[.8, .1, .5]),
                       dict(names=["wrong"]*15), dict(p0=[0, .4, .6])]:
            with self.assertRaises(ValueError):
                self.build(**change)

    def test_triage_never_approves(self):
        rows = [{"market_id": str(i), "question": "Who wins?"} for i in range(2)]
        group = review_group("kalshi:event:KXMVE-TEST", rows, {})
        self.assertFalse(group["family_verified"])
        self.assertIsNone(group["approved_family_id"])
        self.assertIn("multi_leg_contract_requires_verified_component_graph", group["flags"])
        self.assertIn("repeated_question_requires_contract_subtitle", group["flags"])


if __name__ == "__main__":
    unittest.main()
