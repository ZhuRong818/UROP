import unittest
from eventx.v6.subject_retrieval_v02 import subjects,context_gate,missing_class
from eventx.tasks.test_proposition_matcher import article,card

class ExtensionTests(unittest.TestCase):
    def test_actor(self):self.assertIn('Jane Doe',[x['alias'] for x in subjects(card('Will Jane Doe say inflation at her press conference?'))])
    def test_golf(self):self.assertIn('Jane Doe',[x['alias'] for x in subjects(card('The Open Championship: Will Jane Doe finish top 20?'))])
    def test_election(self):self.assertIn('Jane Doe',[x['alias'] for x in subjects(card('Will the margin of victory for Jane Doe in the election exceed 5%?'))])
    def test_price(self):self.assertIn('brent crude oil',[x['alias'] for x in subjects(card('Will the brent crude oil close price be above 90?'))])
    def test_quote_offsets(self):
        c=card('Will Jane Doe play for Team in 2027?')
        for x in subjects(c):self.assertEqual(c[x['field']][x['start']:x['end']],x['source_quote'])
    def test_fixture_abstain(self):self.assertEqual(missing_class(card('Will over 2.5 goals be scored?')),'fixture_identity_missing_from_question')
    def test_combo(self):self.assertEqual(subjects(card('yes Jane,yes Joe')),[])
    def test_sport_context(self):self.assertEqual(context_gate(article('Japan ships oil'),card('Will Japan win on 2026-06-21?'),[{'quote':'Japan'}]),'reject_missing_specific_domain_context')
    def test_music_context(self):self.assertEqual(context_gate(article('Faraday Future robotics'),card('Will Future be #1 on Spotify?'),[{'quote':'Future'}]),'reject_missing_specific_domain_context')
    def test_true_sport_context(self):self.assertEqual(context_gate(article('Japan wins football match'),card('Will Japan win on 2026-06-21?'),[{'quote':'Japan'}]),'subject_context_candidate')

if __name__=='__main__':unittest.main()
