import unittest
from eventx.v6.measurement_extractor import assess, extract

class ExtractionTests(unittest.TestCase):
    registry={'company:example':['Example','EXM'], 'team:argentina':['Argentina team'],
              'company:bbva':['Banco BBVA Argentina']}
    contract='Will Example report revenue above USD 100 in Q1 2026?'
    def test_direct_negative_direction(self):
        r=assess('Example Q1 2026 revenue fell.',self.contract,self.registry)
        self.assertEqual(r['semantic_status'],'direct_candidate')
        self.assertFalse(r['predictive_admitted'])
    def test_alias(self):
        self.assertEqual(assess('EXM Q1 2026 revenue rose.',self.contract,self.registry)['semantic_status'],'direct_candidate')
    def test_wrong_quarter(self):
        self.assertEqual(assess('Example Q2 2026 revenue fell.',self.contract,self.registry)['reason'],'period_mismatch')
    def test_background(self):
        self.assertEqual(assess('Example opens offices.',self.contract,self.registry)['semantic_status'],'background_candidate')
    def test_missing_year(self):
        self.assertEqual(extract('Example Q1 revenue',self.registry)['fields']['period']['status'],'unknown')
    def test_conflicting_period(self):
        self.assertEqual(extract('Q1 2026 versus Q2 2026',self.registry)['fields']['period']['status'],'conflicting')
    def test_entity_collision(self):
        r=dict(self.registry);r['team:example']=['Example']
        self.assertEqual(extract('Example',r)['fields']['entity']['status'],'conflicting')
    def test_no_substring_ticker(self):
        self.assertEqual(extract('EXMORE',self.registry)['fields']['entity']['status'],'unknown')
    def test_no_cross_sentence_binding(self):
        self.assertEqual(assess('Example opens offices. Q1 2026 revenue fell.',self.contract,self.registry)['semantic_status'],'insufficient_evidence')
    def test_quote_integrity(self):
        text='EXM Q1 2026 revenue fell.'
        for field in extract(text,self.registry)['fields'].values():
            if field['status']=='known': self.assertIn(field['quote'],text)
    def test_multiple_metrics(self):
        self.assertEqual(extract('Example revenue and earnings',self.registry)['fields']['metric']['status'],'conflicting')
    def test_no_threshold_entailment_required(self):
        self.assertEqual(assess('Example forecasts Q1 2026 revenue decline.',self.contract,self.registry)['semantic_status'],'direct_candidate')

if __name__=='__main__': unittest.main()
