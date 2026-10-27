import unittest
from eventx.v6.subject_retrieval import subjects,build_registry,retrieve
from eventx.tasks.test_proposition_matcher import card,article

class RetrievalTests(unittest.TestCase):
    def check(self,q,text):
        c=card(q);return retrieve(article(text),build_registry([c]))
    def test_speech(self):self.assertTrue(self.check('What will Example Corporation say during their next earnings call?','Example Corporation earnings'))
    def test_sports(self):self.assertTrue(self.check('Will the Argentina win the World Cup?','Argentina plays tomorrow'))
    def test_wrong_entity(self):self.assertFalse(self.check('Will Argentina win the World Cup?','France plays tomorrow'))
    def test_boundary(self):self.assertFalse(self.check('Will WT win the World Cup?','WTS rises'))
    def test_short_case(self):self.assertFalse(self.check('Will US win the World Cup?','tell us tomorrow'))
    def test_generic(self):self.assertFalse(self.check('Will any team win the World Cup?','any team can win'))
    def test_no_forced_top_one(self):self.assertFalse(self.check('Will Jane post 10 tweets?','Crude oil falls'))
    def test_artist(self):self.assertTrue(self.check('Will Album by Artist have 10 Album Equivalent Units?','Artist announces release'))
    def test_conflict(self):
        c=card('Will Jane post 10 tweets?');c['subtitle_conflict']=True
        self.assertFalse(retrieve(article('Jane posts'),build_registry([c])))
    def test_offsets(self):
        c=card('Will Jane post 10 tweets?');r=retrieve(article('Jane posts'),build_registry([c]))
        h=next(iter(r.values()))[0];self.assertEqual(h['quote'],'Jane');self.assertEqual(h['start'],0)

if __name__=='__main__':unittest.main()
