import unittest
from eventx.tasks.test_proposition_matcher import article,card
from eventx.v6.proposition_matcher_v02 import match

class SeparationTests(unittest.TestCase):
    def test_missing_close_does_not_hide_semantics(self):
        c=card('Will Bitcoin reach $100,000 by December 31, 2026?')
        c['terminal_fields']={'end_date':'2026-12-31T00:00:00Z'}
        r=match(article('Bitcoin Tops $77K'),c)
        self.assertEqual(r['semantic_status'],'direct_candidate')
        self.assertIn('trading_close_not_verified',r['eligibility_reasons'])
        self.assertFalse(r['predictive_admitted'])
    def test_wrong_entity_ranking(self):
        c=card('Will Example have the best AI in June 2026?',rules=['Arena'])
        r=match(article('Example says Rival ranks first on Arena in June 2026'),c)
        self.assertNotEqual(r['semantic_status'],'direct_candidate')
    def test_direct_ranking(self):
        c=card('Will Example have the best AI in June 2026?',rules=['Arena'])
        self.assertEqual(match(article('Example ranks first on Arena in June 2026'),c)['semantic_status'],'direct_candidate')
    def test_background(self):
        c=card('Will Bitcoin reach $100,000 by December 31, 2026?')
        self.assertEqual(match(article('Bitcoin conference opens'),c)['semantic_status'],'background')
    def test_price_subject_binding(self):
        c=card('Will Bitcoin reach $100,000 by December 31, 2026?')
        self.assertNotEqual(match(article('Bitcoin investors watch Ethereum tops $7K'),c)['semantic_status'],'direct_candidate')
    def test_no_certificate_invention(self):
        c=card('Will Bitcoin reach $100,000 by December 31, 2026?')
        self.assertEqual(match(article('Bitcoin falls to $70K'),c)['supported_links'],[])

if __name__=='__main__':unittest.main()
