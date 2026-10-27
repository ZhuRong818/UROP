import unittest
from eventx.tasks.test_proposition_matcher import article,card
from eventx.v6.proposition_matcher_v03 import match,aliases,alias_hits

class ExtensionTests(unittest.TestCase):
    def test_market_cap(self):
        c=card("Will Example's market cap be above $100 on July 1, 2026?")
        self.assertEqual(match(article("Example's market cap fell to $90 on July 1, 2026"),c)['semantic_status'],'direct_candidate')
    def test_wrong_measure(self):
        c=card("Will Example's market cap be above $100 on July 1, 2026?")
        self.assertNotEqual(match(article("Example's share price is $90 on July 1, 2026"),c)['semantic_status'],'direct_candidate')
    def test_unknown_ipo_period(self):
        c=card("Will Example's market cap be above $100 at end of IPO month?")
        self.assertNotEqual(match(article("Example's market cap is $90"),c)['semantic_status'],'direct_candidate')
    def test_net_worth(self):
        c=card('Will Jane have a net worth above $100 on July 1, 2026?')
        self.assertEqual(match(article("Jane's net worth is $90 on July 1, 2026"),c)['semantic_status'],'direct_candidate')
    def test_sales_positive(self):
        c=card('Will Album by Artist have above 100 Pure Album Sales during July 1, 2026 - July 7, 2026?')
        self.assertEqual(match(article('Album by Artist sold 90 pure album sales during July 1, 2026 - July 7, 2026'),c)['semantic_status'],'direct_candidate')
    def test_wrong_artist(self):
        c=card('Will Album by Artist have above 100 Pure Album Sales during July 1, 2026?')
        self.assertNotEqual(match(article('Album by Other sold 90 pure album sales during July 1, 2026'),c)['semantic_status'],'direct_candidate')
    def test_wrong_sales_period(self):
        c=card('Will Album by Artist have above 100 Pure Album Sales during July 1, 2026 - July 7, 2026?')
        self.assertNotEqual(match(article('Album by Artist sold 90 pure album sales during August 1, 2026'),c)['semantic_status'],'direct_candidate')
    def test_index_negative_direction(self):
        c=card('Will Example be added to the S&P 500 in Q2 2026?')
        self.assertEqual(match(article('Example will not be added to the S&P 500 in Q2 2026'),c)['semantic_status'],'direct_candidate')
    def test_peace(self):
        c=card('Alpha x Beta permanent peace deal by July 1, 2026?')
        self.assertEqual(match(article('Alpha and Beta rejected a peace deal on July 1, 2026'),c)['semantic_status'],'direct_candidate')
    def test_different_parties(self):
        c=card('Alpha x Beta permanent peace deal by July 1, 2026?')
        self.assertNotEqual(match(article('Alpha and Gamma signed a peace deal on July 1, 2026'),c)['semantic_status'],'direct_candidate')
    def test_announcement(self):
        c=card('Will Jane announce that the bridge is open by July 1, 2026?')
        self.assertEqual(match(article('Jane announced that the bridge is open on July 1, 2026'),c)['semantic_status'],'direct_candidate')
    def test_alias_trace(self):
        a=aliases('Example Holdings Inc.','market_cap')
        h=alias_hits('Example Holdings market cap',a)
        self.assertTrue(h);self.assertFalse(h[0]['identity_verified'])
        self.assertEqual(h[0]['source_quote'],'Example Holdings Inc.')
    def test_no_ticker_substring(self):
        self.assertEqual(alias_hits('WTS',aliases('WT','company')),[])
    def test_slug_alias_not_model_family(self):
        a=aliases('claude-opus-4-6-thinking','ai_ranking')
        self.assertTrue(alias_hits('Claude Opus 4 6 Thinking',a))
        self.assertEqual(alias_hits('Claude',a),[])
    def test_no_predictive_admission(self):
        c=card('Alpha x Beta permanent peace deal by July 1, 2026?')
        r=match(article('Alpha and Beta signed a peace deal on July 1, 2026'),c)
        self.assertFalse(r['predictive_admitted']);self.assertEqual(r['supported_links'],[])

if __name__=='__main__':unittest.main()
