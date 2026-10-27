import unittest
from eventx.v6.claim_period import period,assess
from eventx.tasks.test_proposition_matcher import article,card

class PeriodTests(unittest.TestCase):
    def check(self,q,t):
        a=article('News');a['source_clock_available_at']=t;c=card(q);c['terminal_fields']={}
        return period(a,c)['status']
    def test_expired_without_close(self):self.assertEqual(self.check('Deal by May 31, 2026?','2026-07-09T00:00:00Z'),'expired_question_period')
    def test_month_end(self):self.assertEqual(self.check('Best AI at the end of June 2026?','2026-07-09T00:00:00Z'),'expired_question_period')
    def test_future(self):self.assertEqual(self.check('Deal by July 31, 2026?','2026-07-09T00:00:00Z'),'before_question_deadline')
    def test_boundary(self):self.assertEqual(self.check('Deal by July 9, 2026?','2026-07-09T00:00:00Z'),'boundary_timezone_unresolved')
    def test_timezone_buffer(self):self.assertEqual(self.check('Deal by July 9, 2026?','2026-07-10T00:00:00Z'),'boundary_timezone_unresolved')
    def test_relative(self):self.assertEqual(self.check('Value on IPO day?','2026-07-09T00:00:00Z'),'unresolved_period')
    def test_multiple(self):self.assertEqual(self.check('Deal by July 9, 2026 or by July 31, 2026?','2026-07-09T00:00:00Z'),'unresolved_period')
    def test_invalid_date(self):self.assertEqual(self.check('Deal by February 30, 2026?','2026-07-09T00:00:00Z'),'unresolved_period')
    def test_opinion(self):
        e={'quote':'Jane says Example leads AI','field':'headline','start':0,'end':26}
        r=assess(article(e['quote']),card('Best AI?'),{'status':'event_channel_candidate','channel':'ranking','evidence':[e]})
        self.assertEqual(r['role'],'opinion_or_attributed_assessment');self.assertFalse(r['predictive_admitted'])
    def test_update_not_settlement(self):
        r=assess(article('US Iran peace progress'),card('Peace?'),{'status':'event_channel_candidate','channel':'peace','evidence':[{'quote':'US Iran peace progress'}]})
        self.assertEqual(r['role'],'event_update_candidate');self.assertFalse(r['settlement_verified'])

if __name__=='__main__':unittest.main()
