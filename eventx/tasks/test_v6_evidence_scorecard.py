import unittest
from eventx.tasks.score_v6_evidence_fields import classify, score
from eventx.v6.structured_evidence import extract


class ScorecardTests(unittest.TestCase):
    def test_missing_predicate_is_not_correct_unknown(self):
        self.assertEqual(classify(None, None, False), 'missing_predicate')

    def test_unknown_correct(self):
        self.assertEqual(classify(None, None), 'correct')

    def test_missing_field(self):
        self.assertEqual(classify(None, 'fund'), 'missing_field')

    def test_wrong_field(self):
        self.assertEqual(classify('copper', 'silver'), 'incorrect')

    def test_punctuation_only(self):
        self.assertEqual(classify('copper.', 'copper'), 'correct')
        self.assertEqual(classify('Copper', 'copper'), 'incorrect')

    def test_exact_offset_and_negative_predicate(self):
        case = ('nominal', 'The company celebrates design wins.', 'wins', {'predicate_absent': True})
        self.assertEqual(score(case, extract({'headline': case[1]}))[0]['status'], 'incorrect')


if __name__ == '__main__':
    unittest.main()
