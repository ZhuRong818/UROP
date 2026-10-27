import unittest
import en_core_web_sm
from eventx.v6.compositional_evidence import extract as previous
from eventx.v6.compositional_evidence_v02 import revise, assess_role
from eventx.v6.structured_evidence import validate_spans


class UncertaintyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = en_core_web_sm.load()

    def get(self, text, predicate):
        a = {'headline': text}
        old = previous(a, self.nlp)
        new = revise(old)
        self.assertEqual(old['schema_version'], 'compositional-evidence-0.1')
        validate_spans(new, a)
        return next(c for c in new['claims'] if c['predicate']['value'] == predicate)

    def test_partitive_preserved_as_alternative(self):
        c = self.get('The fund sold some of its copper holdings.', 'sold')
        self.assertEqual(c['object']['value'], 'some')
        alt = c['roles']['object']['complement_candidates'][0]
        self.assertEqual(alt['span']['value'], 'some of its copper holdings')
        self.assertEqual(alt['attachment'], 'unresolved')
        self.assertIsNone(c['roles']['object']['resolved_entity']['value'])

    def test_notification_not_expanded_entity(self):
        c = self.get('The director notified the company of his resignation.', 'notified')
        self.assertEqual(c['object']['value'], 'the company')
        self.assertFalse(c['relation_readiness']['may_auto_link_contract'])

    def test_time_adjunct(self):
        c = self.get('Brazil won the quarterfinal in 2026.', 'won')
        self.assertEqual(c['object']['value'], 'the quarterfinal')

    def test_nominal_metaphor_not_verified(self):
        c = self.get('History says prices will fall.', 'says')
        self.assertFalse(c['speaker_assessment']['verified_speaker'])
        self.assertEqual(c['speaker_assessment']['communicator_type'], 'unverified')

    def test_negated_attribution(self):
        c = self.get('The analyst did not say copper rose.', 'rose')
        edge = c['attribution_chain'][0]
        self.assertFalse(edge['verified_attribution'])
        self.assertIsNone(c['polarity']['value'])
        self.assertEqual(edge['negation']['value'], 'syntactic_negation')

    def test_pronoun_unknown(self):
        c = self.get('It purchased silver.', 'purchased')
        self.assertIn('referent_unresolved', c['roles']['actor']['assessment']['risks'])

    def test_bad_head(self):
        t = dict(field='headline', start=0, end=2, quote='Is', head_start=3, pos='AUX')
        role = dict(value='Is', evidence=[{k:t[k] for k in ('field','start','end','quote')}])
        self.assertIn('non_nominal_head', assess_role(role, [t])['risks'])

    def test_reject_wrong_schema(self):
        with self.assertRaises(ValueError):
            revise({'schema_version': 'other'})


if __name__ == '__main__':
    unittest.main()
