import hashlib
import unittest

from eventx.v6.contracts import canonical_id, outcome_mapping, predictive_text, review_text
from eventx.v6.retrieval import BM25


class ContractTests(unittest.TestCase):
    def test_namespaces(self):
        self.assertEqual(canonical_id("kalshi", "event", "ABC"), "kalshi:event:ABC")
        self.assertEqual(canonical_id("kalshi", "event", "kalshi:event:ABC"), "kalshi:event:ABC")
        with self.assertRaises(ValueError):
            canonical_id("kalshi", "event", "polymarket:event:ABC")

    def test_mapping_not_position_guess(self):
        self.assertEqual(outcome_mapping('["No","Yes"]', '["1","2"]'), {"no": "1", "yes": "2"})
        with self.assertRaises(ValueError):
            outcome_mapping(["Yes", "No"], ["1", "1"])
        with self.assertRaises(ValueError):
            outcome_mapping(["A", "B"], ["1", "2"])

    def test_subtitles_change_retrieval(self):
        a = {"question": "Who wins the election?", "yes_subtitle": "Alice"}
        b = {"question": "Who wins the election?", "yes_subtitle": "Bob"}
        self.assertNotEqual(review_text(a), review_text(b))
        engine = BM25([review_text(a), review_text(b)])
        self.assertEqual(engine.search("Bob wins")[0][0], 1)

    def test_review_not_predictive(self):
        with self.assertRaises(ValueError):
            predictive_text({"question": "Q", "pit_certificate": None}, "2026-06-01T00:00:00Z")

    def test_certificate_time_and_hash(self):
        card = {"question": "Q", "pit_certificate": {"verified": True, "evidence_ref": "test",
            "available_at": "2026-06-02T00:00:00Z", "valid_from": "2026-06-01T00:00:00Z",
            "valid_until": "2026-07-01T00:00:00Z", "text_sha256": hashlib.sha256(b"Q").hexdigest()}}
        with self.assertRaises(ValueError):
            predictive_text(card, "2026-06-01T12:00:00Z")
        self.assertEqual(predictive_text(card, "2026-06-02T00:00:00Z"), "Q")
        with self.assertRaises(ValueError):
            predictive_text(card, "2026-07-01T00:00:00Z")
        card["rule_evidence"] = [{"text": "Later revised rule"}]
        with self.assertRaises(ValueError):
            predictive_text(card, "2026-06-03T00:00:00Z")

    def test_empty_and_deterministic_retrieval(self):
        engine = BM25(["same text", "same text"])
        self.assertEqual(engine.search("missing"), [])
        self.assertEqual([i for i, _ in engine.search("same")], [0, 1])


if __name__ == "__main__":
    unittest.main()
