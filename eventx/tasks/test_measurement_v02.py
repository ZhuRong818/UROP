import unittest
from eventx.v6.measurement_v02 import company_registry, extract, assess_card

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.card={'contract_id':'synthetic:c','question':'Will Example Holdings Inc. report revenue in Q1 2026?',
                   'yes_subtitle':'Above USD 100','rule_evidence':[]}
        self.registry,self.evidence=company_registry([self.card])
    def test_suffix_alias(self):
        self.assertEqual(extract('Example Holdings revenue in Q1 2026',self.registry)['fields']['entity']['status'],'known')
        self.assertFalse(self.evidence[0]['independently_verified'])
    def test_spelled_quarter(self):
        self.assertEqual(extract('second quarter of 2026',{})['fields']['period']['value'],'2026Q2')
    def test_conflicting_quarters(self):
        self.assertEqual(extract('first quarter 2026 and Q2 2026',{})['fields']['period']['status'],'conflicting')
    def test_abbreviation_claim(self):
        self.assertIsNotNone(extract(self.card['question'],self.registry)['claim_span'])
    def test_negative_direction_candidate(self):
        r=assess_card({'headline':'Example Holdings first quarter 2026 revenue fell.'},self.card,self.registry)
        self.assertEqual(r['semantic_status'],'direct_candidate')
        self.assertEqual(r['supported_links'],[])
    def test_rules_preserved(self):
        self.card['rule_evidence']=[{'text':'Q2 2026','path':'synthetic'}]
        r=assess_card({'headline':'Example Holdings Q1 2026 revenue fell.'},self.card,self.registry)
        self.assertEqual(r['contract_source_fields'][2]['provenance']['path'],'synthetic')
        self.assertEqual(r['contract_extraction']['fields']['period']['status'],'conflicting')
        self.assertNotEqual(r['semantic_status'],'direct_candidate')
    def test_subtitle_conflict(self):
        self.card['subtitle_conflict']=True
        self.assertEqual(assess_card({},self.card,self.registry)['reason'],'conflicting_subtitles')
    def test_no_year_inference(self):
        self.assertEqual(extract('first quarter revenue',{})['fields']['period']['status'],'unknown')

if __name__=='__main__': unittest.main()
