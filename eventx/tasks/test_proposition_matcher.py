import unittest
from eventx.v6.proposition_matcher import match

def card(q,subtitle='',rules=None):
    return {'contract_id':'synthetic:c','question':q,'yes_subtitle':subtitle,
            'rule_evidence':[{'text':x} for x in (rules or [])],
            'terminal_fields':{'close_time':'2026-12-31T23:59:59Z'}}

def article(text):return {'headline':text,'source_clock_available_at':'2026-06-15T12:00:00Z'}

class MatcherTests(unittest.TestCase):
    def setUp(self):self.c=card('Will Bitcoin reach $100,000 by December 31, 2026?')
    def test_price_positive(self):
        self.assertEqual(match(article('Bitcoin Tops $77K'),self.c)['status'],'direct_candidate')
    def test_negative_direction(self):
        self.assertEqual(match(article('Bitcoin falls to $70K'),self.c)['status'],'direct_candidate')
    def test_no_admission(self):
        r=match(article('Bitcoin Tops $77K'),self.c)
        self.assertEqual(r['supported_links'],[]);self.assertFalse(r['predictive_admitted'])
    def test_wrong_entity(self):
        self.assertNotEqual(match(article('Ethereum Tops $7K'),self.c)['status'],'direct_candidate')
    def test_different_entity_in_clause(self):
        self.assertNotEqual(match(article('Bitcoin investors watch Ethereum price rises to $7K'),self.c)['status'],'direct_candidate')
    def test_old_price(self):
        self.assertNotEqual(match(article('Bitcoin topped $77K in 2024'),self.c)['status'],'direct_candidate')
    def test_background(self):
        self.assertEqual(match(article('Bitcoin conference opens'),self.c)['status'],'background')
    def test_closed(self):
        a=article('Bitcoin Tops $77K');a['source_clock_available_at']='2027-01-01T00:00:00Z'
        self.assertEqual(match(a,self.c)['reason'],'article_after_recorded_close')
    def test_unknown_date(self):
        self.assertNotEqual(match(article('Bitcoin Tops $77K'),card('Will Bitcoin reach $100,000 soon?'))['status'],'direct_candidate')
    def test_missing_clock(self):
        self.assertEqual(match({'headline':'Bitcoin Tops $77K'},self.c)['status'],'insufficient_evidence')
    def test_ranking(self):
        c=card('Will Example have the best AI in June 2026?',rules=['The Arena leaderboard determines the winner.'])
        self.assertEqual(match(article('Example ranks first on Arena in June 2026'),c)['status'],'direct_candidate')
    def test_wrong_ranking_period(self):
        c=card('Will Example have the best AI in June 2026?',rules=['Arena leaderboard'])
        self.assertNotEqual(match(article('Example ranks first on Arena in May 2026'),c)['status'],'direct_candidate')
    def test_chart(self):
        c=card('Will Example Song be #1 on Billboard Hot 100 on July 4, 2026?')
        self.assertEqual(match(article('Example Song reaches Billboard Hot 100 on July 4, 2026'),c)['status'],'direct_candidate')
    def test_leadership(self):
        c=card('Who will be the next Director of National Intelligence by July 1, 2026?','Jane Doe')
        self.assertEqual(match(article('Jane Doe nomination for Director of National Intelligence on July 1, 2026'),c)['status'],'direct_candidate')
    def test_wrong_office(self):
        c=card('Who will be the next Director of National Intelligence by July 1, 2026?','Jane Doe')
        self.assertNotEqual(match(article('Jane Doe nomination for CFPB director on July 1, 2026'),c)['status'],'direct_candidate')
    def test_tweets(self):
        c=card('Will Jane Doe post 100 tweets in June 2026?')
        self.assertEqual(match(article('Jane Doe posted 80 tweets in June 2026'),c)['status'],'direct_candidate')
    def test_not_cross_sentence(self):
        self.assertNotEqual(match(article('Bitcoin conference. Ethereum Tops $7K'),self.c)['status'],'direct_candidate')
    def test_subtitle_conflict(self):
        self.c['subtitle_conflict']=True
        self.assertNotEqual(match(article('Bitcoin Tops $77K'),self.c)['status'],'direct_candidate')

if __name__=='__main__':unittest.main()
