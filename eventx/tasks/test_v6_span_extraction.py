import unittest
from eventx.tasks.trial_v6_span_extraction import validate


class SpanTests(unittest.TestCase):
    def test_exact(self):
        obj,e = validate('{"source":null,"traded_object":"silver","mode":"literal"}', 'It bought silver.')
        self.assertEqual(e['traded_object'][0]['start'],10)

    def test_invented_name(self):
        with self.assertRaises(ValueError):
            validate('{"source":"John","traded_object":null,"mode":"literal"}', 'It spoke.')

    def test_missing_key(self):
        with self.assertRaises(ValueError):
            validate('{}','text')

    def test_markdown_rejected(self):
        with self.assertRaises(ValueError):
            validate('```json\n{}\n```','text')

    def test_all_occurrences(self):
        _,e = validate('{"source":"Ann","traded_object":null,"mode":"literal"}', 'Ann met Ann.')
        self.assertEqual(len(e['source']),2)


if __name__ == '__main__':
    unittest.main()
