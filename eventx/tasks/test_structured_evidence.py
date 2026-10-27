import unittest
from eventx.v6.structured_evidence import extract, compare_contract, validate_spans


class Tests(unittest.TestCase):
    def claim(self, text):
        a = {'headline': text}; e = extract(a); validate_spans(e, a)
        self.assertFalse(e['predictive_admitted'])
        return e['claims'][0]

    def test_passive(self):
        c = self.claim('Copper was purchased by a pension fund.')
        self.assertEqual(c['actor']['value'], 'a pension fund')
        self.assertEqual(c['object']['value'], 'Copper')

    def test_active(self):
        c = self.claim('A pension fund purchased copper.')
        self.assertEqual(c['actor']['value'], 'A pension fund')
        self.assertEqual(c['object']['value'], 'copper')

    def test_opinion(self):
        c = self.claim('Analyst argues copper is overvalued.')
        self.assertEqual(c['speaker']['value'], 'Analyst')
        self.assertEqual(c['epistemic_status']['value'], 'opinion')
        self.assertEqual(c['object']['status'], 'unknown')

    def test_forecast(self):
        c = self.claim('Economist expects copper to appreciate.')
        self.assertEqual(c['epistemic_status']['value'], 'forecast')

    def test_no_event_year_invention(self):
        e = extract({'headline': 'Team won in 2022.'})
        self.assertEqual(compare_contract(e, 'Win in 2026?')['year_mention_relation'], 'disjoint_mentions')
        self.assertEqual(compare_contract(e, 'Win in 2022?')['episode_identity'], 'unknown')

    def test_unknown(self):
        c = self.claim('A bullish thesis for copper')
        self.assertEqual(c['actor']['status'], 'unknown')

    def test_negation(self):
        c = self.claim('Analyst argues copper is not overvalued.')
        self.assertEqual(c['polarity']['value'], 'negation_present_scope_unknown')

    def test_sidebars(self):
        self.assertEqual(extract({'summary': 'Related Articles Copper was purchased by a fund.'})['claims'], [])

    def test_decimal(self):
        c = self.claim('Copper falls to 3.25 dollars.')
        self.assertEqual(c['object']['value'], 'to 3.25 dollars')


if __name__ == '__main__': unittest.main()
