import copy
import unittest
from eventx.v6.link_audit import validate_reviews

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.packet=[{"pair_id":"x","article":{"headline":"Alice wins poll","summary":"Survey released today"}}]
        self.a=[{"pair_id":"x","reviewer_id":"A","labels":{"relevance":"direct",
            "outcome_applicability":"yes_proposition","evidence_spans":["Alice wins poll"]}}]
        self.b=copy.deepcopy(self.a)
        self.b[0]["reviewer_id"]="B"

    def test_valid(self):
        self.assertFalse(validate_reviews(self.packet,self.a,self.b)["adjudication_required"])

    def test_no_fabricated_quotes(self):
        self.b[0]["labels"]["evidence_spans"]=["Invented statement"]
        with self.assertRaises(ValueError): validate_reviews(self.packet,self.a,self.b)

    def test_distinct_ids_required(self):
        with self.assertRaises(ValueError): validate_reviews(self.packet,self.a,self.a)

    def test_disagreement_retained(self):
        self.b[0]["labels"]["relevance"]="background"
        self.assertEqual(validate_reviews(self.packet,self.a,self.b)["disagreement_ids"],["x"])

    def test_blank_rejected(self):
        self.b[0]["labels"]["relevance"]=None
        with self.assertRaises(ValueError): validate_reviews(self.packet,self.a,self.b)

    def test_missing_duplicate_empty(self):
        for b in ([],self.b+self.b):
            with self.assertRaises(ValueError): validate_reviews(self.packet,self.a,b)
        with self.assertRaises(ValueError): validate_reviews([],[],[])

if __name__ == "__main__": unittest.main()
