"""Synthetic checks for projected historical recovery query generation."""

import unittest

from eventx.tasks.build_v5_recovery_requests import END, event_sql, literal, metadata_sql


class RecoveryRequestTests(unittest.TestCase):
    def test_ids_are_not_interchangeable(self):
        sql = event_sql([("0xcondition", "1234")])
        self.assertIn("('0xcondition', '1234')", sql)
        self.assertIn("member.market_id = t.cached_market_id", sql)

    def test_projection_and_temporal_fence(self):
        for build in [event_sql, metadata_sql]:
            sql = build([("condition", "market")])
            self.assertIn(END, sql)
            self.assertIn("LIMIT 5000", sql)
            for prohibited in ["SELECT *", "outcome_prices", "winning_outcome", "settlement_price"]:
                self.assertNotIn(prohibited, sql)

    def test_literal_escaping(self):
        self.assertEqual(literal("a'b"), "'a''b'")


if __name__ == "__main__":
    unittest.main()
