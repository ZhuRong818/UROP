import unittest
from eventx.v6.clean_speech import clean,prepare
from eventx.tasks.test_proposition_matcher import article,card

class SpeechTests(unittest.TestCase):
    def test_wrong_speaker(self):
        _,r=prepare(article('Jane says Trump is wrong'),card('Will Trump say "Meta" before Aug 1, 2026?'))
        self.assertEqual(r['status'],'abstain')
    def test_correct_speaker(self):
        _,r=prepare(article('Trump said Meta'),card('Will Trump say "Meta" before Aug 1, 2026?'))
        self.assertEqual(r['status'],'event_channel_candidate')
    def test_wrong_occasion(self):
        _,r=prepare(article('Tim Cook said sales fell in April'),card('What will Tim Cook say during Apple WWDC26 Keynote?'))
        self.assertEqual(r['status'],'abstain')
    def test_occasion(self):
        _,r=prepare(article('Tim Cook said hello during Apple WWDC26 Keynote'),card('What will Tim Cook say during Apple WWDC26 Keynote?'))
        self.assertEqual(r['status'],'event_channel_candidate')
    def test_mask(self):
        a=article('News');a['summary']='Real text. Most Read from Bloomberg Trump says Meta'
        c,e=clean(a);self.assertEqual(len(c['summary']),len(a['summary']));self.assertNotIn('Trump',c['summary']);self.assertEqual(a['summary'][e[0]['start']:e[0]['end']],'Most Read from Bloomberg Trump says Meta')
    def test_raw_unchanged(self):
        a=article('Most Read from News');clean(a);self.assertEqual(a['headline'],'Most Read from News')

if __name__=='__main__':unittest.main()
