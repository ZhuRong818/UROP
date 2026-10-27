"""Synthetic unit checks; no real source or outcome inputs."""

import unittest

from eventx.tasks.prepare_v5_source_readiness import family_candidate, inspect_news, timestamp


class SourceReadinessTests(unittest.TestCase):
    def test_event_keys_are_candidates_not_verified_families(self):
        candidate = family_candidate("kalshi", {"event_ticker": "EVENT"})
        self.assertEqual(candidate["candidate_family_id"], "kalshi:event:EVENT")
        self.assertFalse(candidate["family_verified"])

    def test_no_slug_or_contract_hash_fallback(self):
        candidate = family_candidate("polymarket", {"slug": "election", "condition_id": "0x123"})
        self.assertIsNone(candidate["candidate_family_id"])
        self.assertFalse(candidate["family_verified"])

    def test_source_clock_must_include_run_end(self):
        row = {"published_at": "2026-06-01T10:00:00Z", "ingest_ts": "2026-06-01T10:03:00Z",
               "run_started_at": "2026-06-01T10:02:00Z", "run_ended_at": "2026-06-01T10:04:00Z",
               "available_at": "2026-06-01T10:04:00Z"}
        self.assertTrue(inspect_news(row)[1])
        row["available_at"] = row["published_at"]
        self.assertFalse(inspect_news(row)[1])

    def test_ambiguous_clock_rejected(self):
        with self.assertRaises(ValueError):
            timestamp("2026-06-01T10:00:00")
        with self.assertRaises(ValueError):
            timestamp(None)


if __name__ == "__main__":
    unittest.main()
