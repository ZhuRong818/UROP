import unittest
from eventx.v6.subject_context import context_gate
from eventx.tasks.test_proposition_matcher import article,card

class ContextTests(unittest.TestCase):
    def check(self,q,text,quote):return context_gate(article(text),card(q),[{'quote':quote}])
    def test_generic(self):self.assertEqual(self.check('Will there be goals?','There is news','There'),'reject_generic_subject')
    def test_country(self):self.assertEqual(self.check('Will Iran win the World Cup?','Iran peace deal','Iran'),'reject_missing_contract_domain_context')
    def test_sports(self):self.assertEqual(self.check('Will Iran win the World Cup?','Iran World Cup match','Iran'),'subject_context_candidate')
    def test_future(self):self.assertEqual(self.check('Will Future have a #1 album?','future stock returns','future'),'reject_missing_contract_domain_context')
    def test_music(self):self.assertEqual(self.check('Will Future have a #1 album?','Future releases an album','Future'),'subject_context_candidate')
    def test_tweets(self):self.assertEqual(self.check('Will Elon Musk post 100 tweets?','Elon Musk launches rocket','Elon Musk'),'reject_missing_contract_domain_context')

if __name__=='__main__':unittest.main()
