import unittest
from eventx.tasks.trial_v6_nli_binding import decision, CASES, AMBIGUOUS


class NliDecisionTests(unittest.TestCase):
    def test_support(self):
        self.assertEqual(decision(dict(entailment=.9,neutral=.05,contradiction=.05)), 'supported_candidate')

    def test_below_threshold(self):
        self.assertEqual(decision(dict(entailment=.79,neutral=.11,contradiction=.1)), 'abstain')

    def test_neutral_abstains(self):
        self.assertEqual(decision(dict(entailment=.05,neutral=.9,contradiction=.05)), 'abstain')

    def test_contradiction_abstains(self):
        self.assertEqual(decision(dict(entailment=.05,neutral=.05,contradiction=.9)), 'abstain')

    def test_fixed_case_ids(self):
        ids = [c[0] for c in CASES + AMBIGUOUS]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(2*len(CASES)+len(AMBIGUOUS),18)


if __name__ == '__main__':
    unittest.main()
