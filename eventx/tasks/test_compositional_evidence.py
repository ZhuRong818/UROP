import unittest
import en_core_web_sm
from eventx.v6.compositional_evidence import extract
from eventx.v6.structured_evidence import validate_spans


class CompositionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = en_core_web_sm.load()

    def get(self, text, predicate):
        a = {'headline': text}
        e = extract(a, self.nlp)
        validate_spans(e, a)
        return next(c for c in e['claims'] if c['predicate']['value'] == predicate)

    def test_partitive(self):
        c = self.get('The fund sold some of its copper holdings.', 'sold')
        self.assertEqual(c['object']['value'], 'some of its copper holdings')

    def test_time_not_object(self):
        c = self.get('Brazil won the quarterfinal in 2026.', 'won')
        self.assertEqual(c['object']['value'], 'the quarterfinal')

    def test_forecast_scope(self):
        c = self.get('The economist expects copper to appreciate.', 'appreciate')
        self.assertEqual(c['attribution_chain'][0]['speaker']['value'], 'The economist')
        self.assertEqual(c['attribution_chain'][0]['epistemic_status']['value'], 'forecast')

    def test_negation_not_propagated(self):
        c = self.get('The analyst did not say copper rose.', 'rose')
        self.assertEqual(c['attribution_chain'][0]['negation']['value'], 'syntactic_negation')
        self.assertIsNone(c['polarity']['value'])
        self.assertEqual(c['assertion_commitment'], 'unknown')

    def test_pronoun_not_resolved(self):
        c = self.get('The fund sold copper. It purchased silver.', 'purchased')
        self.assertEqual(c['actor']['value'], 'It')
        self.assertEqual(c['entity_identity'], 'unknown')


if __name__ == '__main__':
    unittest.main()
