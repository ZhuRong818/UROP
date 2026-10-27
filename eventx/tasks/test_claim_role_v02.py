import unittest
from eventx.v6.claim_role_v02 import classify

class RoleTests(unittest.TestCase):
    def check(self,text):return classify({'quote':text},'speech')
    def test_attributed_action(self):self.assertEqual(self.check('Officials said talks resumed')['role'],'reported_action_or_observation')
    def test_unattributed_action(self):self.assertEqual(self.check('Talks resumed')['role'],'reported_action_or_observation')
    def test_forecast(self):self.assertEqual(self.check('Officials said talks will resume')['role'],'prospective_or_modal_claim')
    def test_modal(self):self.assertEqual(self.check('Officials said talks could resume')['role'],'prospective_or_modal_claim')
    def test_opinion(self):self.assertEqual(self.check('Musk says Example is best')['role'],'evaluative_assessment')
    def test_contamination(self):self.assertEqual(self.check('Most Read from Bloomberg Trump said talks resumed')['role'],'contaminated_summary_context')
    def test_said_not_enough(self):self.assertEqual(self.check('Jane said something')['role'],'unresolved')
    def test_negative_action(self):self.assertEqual(self.check('Officials said the deal was rejected')['role'],'reported_action_or_observation')
    def test_not_truth(self):self.assertFalse(self.check('Officials said talks resumed')['truth_verified'])
    def test_attribution_separate(self):self.assertTrue(self.check('Officials said talks resumed')['attributed'])

if __name__=='__main__':unittest.main()
