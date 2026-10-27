import unittest
from eventx.v6.fetch_priority import mention_role, group_key

class Tests(unittest.TestCase):
    def setUp(self):
        self.card={'question':'Will Reddit be added to the S&P 500 in Q2 2026?', 'contract_id':'c', 'event_ids':['e']}
        self.entries=[{'name':'Reddit'},{'name':'S&P 500'}]
    def test_context(self):
        self.assertEqual(mention_role(self.card,self.entries,[{'contract_evidence':self.entries[1]}]),'context_only')
    def test_primary(self):
        self.assertEqual(mention_role(self.card,self.entries,[{'contract_evidence':self.entries[0]}]),'primary_mention')
    def test_unknown(self):
        self.assertEqual(mention_role({**self.card,'question':'Which index?'},self.entries,[]),'primary_unresolved')
    def test_conflict(self):
        self.assertEqual(mention_role({**self.card,'subtitle_conflict':True},self.entries,[]),'primary_unresolved')
    def test_group(self):
        self.assertEqual(group_key(self.card),'e')
        self.assertEqual(group_key({**self.card,'event_ids':['e','f']}),'c')

if __name__=='__main__':unittest.main()
