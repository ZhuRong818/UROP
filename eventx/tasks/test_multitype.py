import unittest
from eventx.v6.multitype import parse,compare

def card(q,subtitle=''):
    return {'contract_id':'synthetic:x','question':q,'yes_subtitle':subtitle,'rule_evidence':[]}

class RoutingTests(unittest.TestCase):
    def test_routes(self):
        examples={'sports':'Will Alice record three pointers in the Playoffs?',
         'music_ranking':'Will Example be #1 on Billboard?',
         'music_sales':'Will Example have above 3000 Pure Album Sales?',
         'ai_ranking':'Who has the best AI?', 'leadership':'Next Director of National Intelligence?',
         'tweet_count':'Will Alice post 300 tweets?', 'corporate_action':'Will X acquire Y?',
         'measurement':'Will X report revenue?', 'price_threshold':'Will Bitcoin reach $100,000?',
         'event_deadline':'Peace deal by July 1, 2026?', 'speech':'What will X say during the call?'}
        for kind,q in examples.items():
            with self.subTest(kind=kind):self.assertEqual(parse(card(q))['type_hypothesis'],kind)
    def test_offsets(self):
        r=parse(card('Will Bitcoin reach $100,000 by December 31, 2026?'))
        sources={s['field']:s['text'] for s in r['sources']}
        for hits in r['fields'].values():
            for h in hits:self.assertEqual(sources[h['source_field']][h['start']:h['end']],h['quote'])
    def test_no_date_guess(self):
        self.assertEqual(parse(card('Best AI this month?'))['fields']['time_mentions'],[])
    def test_no_link_from_subject(self):
        r=parse(card('Will Bitcoin reach $100,000?'))
        self.assertEqual(compare({'headline':'Bitcoin rises'},r)['supported_links'],[])
    def test_subtitle_retained(self):
        self.assertEqual(parse(card('Best AI?', 'Example model'))['fields']['outcome_candidate'][0]['quote'],'Example model')
    def test_unknown(self):self.assertEqual(parse(card('Unclear?'))['type_hypothesis'],'unknown')

if __name__=='__main__':unittest.main()
