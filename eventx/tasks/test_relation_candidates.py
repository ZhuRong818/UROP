import unittest
from eventx.v6.relation_candidates import constraint
from eventx.tasks.test_proposition_matcher import article,card

class RelationTests(unittest.TestCase):
    def run_pair(self,text):return constraint(article(text),card('US x Iran permanent peace deal by July 1, 2026?'))
    def test_update_without_deadline(self):self.assertEqual(self.run_pair('US and Iran resumed peace talks')['status'],'event_channel_candidate')
    def test_wrong_actor(self):self.assertEqual(self.run_pair('US and Canada resumed peace talks')['status'],'abstain')
    def test_wrong_relation(self):self.assertEqual(self.run_pair('US and Iran reported oil prices')['status'],'abstain')
    def test_cross_sentence(self):self.assertEqual(self.run_pair('US issued a statement. Iran resumed peace talks')['status'],'abstain')
    def test_negative_direction(self):self.assertEqual(self.run_pair('US and Iran suspended peace talks')['status'],'event_channel_candidate')
    def test_not_admitted(self):self.assertFalse(self.run_pair('US and Iran resumed peace talks')['predictive_admitted'])
    def test_offsets(self):
        text='US and Iran resumed peace talks';e=self.run_pair(text)['evidence'][0]
        self.assertEqual(text[e['start']:e['end']],e['quote'])

if __name__=='__main__':unittest.main()
