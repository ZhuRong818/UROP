import unittest

from eventx.v7.signed_evidence_v02 import extract_signed_evidence


class SignedEvidenceV02Test(unittest.TestCase):
    def test_payroll_threshold(self):
        r = extract_signed_evidence("Jobs", "May nonfarm payrolls added 172,000 jobs", "Will US nonfarm payrolls for May 2026 be above 100K?")
        self.assertEqual((r.applicability, r.direction), ("exact", 1))

    def test_later_first_hike_opposes_deadline(self):
        r = extract_signed_evidence("Forecast", "Bank of America predicts the first 25-basis-point hike in September", "Will the Federal Reserve hike rates by June 30, 2026?")
        self.assertEqual((r.applicability, r.direction, r.claim_type), ("exact", -1, "forecast"))

    def test_policy_forecast_survives_dividend_headline(self):
        r = extract_signed_evidence("Dividend giants", "Bank of America predicts the Federal Reserve will raise interest rates, with the first 25-basis-point hike in September", "Will the Federal Reserve hike rates by June 30, 2026?")
        self.assertEqual((r.applicability, r.direction), ("exact", -1))

    def test_hyphenated_basis_point_forecast_matches_bucket(self):
        r = extract_signed_evidence("Forecast", "Bank of America predicts the first 25-basis-point hike in September", "Will the Fed increase interest rates by 25 bps after the September meeting?")
        self.assertEqual((r.applicability, r.direction), ("exact", 1))

    def test_hold_opposes_cut_and_is_not_prediction_market_odds(self):
        r = extract_signed_evidence("Fed", "Traders widely expect the Fed will keep the target unchanged in June", "Will the Fed decrease interest rates by 50 bps after the June meeting?")
        self.assertEqual((r.applicability, r.direction), ("exact", -1))
        self.assertTrue(r.general_market_expectation)
        self.assertFalse(r.explicit_prediction_market_odds)

    def test_unchanged_range_fixes_upper_bound(self):
        r = extract_signed_evidence("Fed", "Traders expect the Fed will keep the federal-funds target unchanged at a range of 3.50% to 3.75% in June", "Will the upper bound of the federal funds rate be above 3.75% following the Fed's June meeting?")
        self.assertEqual((r.applicability, r.direction), ("exact", -1))

    def test_explicit_prediction_market_odds_requires_venue_and_quantity(self):
        r = extract_signed_evidence("Polymarket", "Polymarket odds show a 65% chance the Fed will hike in July", "Will the Fed hike after the July meeting?")
        self.assertTrue(r.explicit_prediction_market_odds)

    def test_corporate_hike_trap_abstains(self):
        r = extract_signed_evidence("JPMorgan dividend hike", "$50 billion buyback after the Fed stress test", "Fed rate hike in 2026?")
        self.assertEqual((r.applicability, r.direction), ("none", 0))

    def test_wrong_country_or_period_abstains(self):
        r = extract_signed_evidence("Jobs", "US May payrolls added 172,000 jobs", "Mexico unemployment rate in May 2026?")
        self.assertEqual((r.applicability, r.direction), ("none", 0))


if __name__ == "__main__":
    unittest.main()
