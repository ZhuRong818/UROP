import unittest
from eventx.tasks.validate_v6_boundary_submissions import validate

class BoundarySubmissionTests(unittest.TestCase):
    def setUp(self):
        self.original=[{"review_id":"s1","development_article":{"headline":"A"},
                        "reviewer":None,"decision":None,"rationale":None}]
        self.row={**self.original[0],"reviewer":"R","decision":"distinct_story","rationale":"Different events"}
    def test_complete(self):
        self.assertEqual(validate(self.original,[self.row],"story"),[])
    def test_changed_evidence(self):
        r={**self.row,"development_article":{"headline":"changed"}}
        self.assertTrue(any(e["error"]=="evidence_changed" for e in validate(self.original,[r],"story")))
    def test_duplicate(self):
        self.assertTrue(validate(self.original,[self.row,self.row],"story"))
    def test_missing(self):
        self.assertTrue(validate(self.original,[],"story"))
    def test_bad_label(self):
        self.assertTrue(validate(self.original,[{**self.row,"decision":"approved"}],"story"))
    def test_blank_reviewer(self):
        self.assertTrue(validate(self.original,[{**self.row,"reviewer":" "}],"story"))

if __name__=="__main__":unittest.main()
