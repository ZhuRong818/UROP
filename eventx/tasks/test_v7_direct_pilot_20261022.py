"""Integrity tests for scope isolation, window boundaries and print matching."""
import unittest
from eventx.tasks.collect_v7_direct_pilot_20261022 import check_scope, ScopeError, valid_trade_window
from eventx.tasks.audit_v7_direct_pilot_20261022 import fingerprint
from eventx.tasks.prepare_v7_direct_pilot_20261022 import classify

class IntegrityTests(unittest.TestCase):
    def test_reject_nested_foreign_market(self):
        with self.assertRaises(ScopeError):
            check_scope([{'price_changes':[{'market':'0x'+'b'*64}]}],{'0x'+'a'*64},{'12','13'})
    def test_reject_foreign_token(self):
        with self.assertRaises(ScopeError):check_scope({'tokens':[{'token_id':'99'}]},{'0x'+'a'*64},{'12','13'})
    def test_accept_scoped_frame(self):
        check_scope({'market':'0x'+'a'*64,'price_changes':[{'asset_id':'12'}]},{'0x'+'a'*64},{'12','13'})
    def test_wrong_window_not_empty_success(self):
        self.assertFalse(valid_trade_window([{'timestamp':999}],1000,1100,'venue'))
        self.assertFalse(valid_trade_window({'error':'failed'},1000,1100,'venue'))
        self.assertFalse(valid_trade_window([{'price':.5}],1000,1100,'venue'))
        self.assertTrue(valid_trade_window([],1000,1100,'venue'))
    def test_equivalent_prints_normalize(self):
        a={'asset':'12','timestamp':1000,'price':'.50','size':'1.00','side':'BUY'}
        b={'token_id':'12','ts':'1970-01-01T00:16:40+00:00','price':.5,'size':1,'side':'buy'}
        self.assertEqual(fingerprint(a),fingerprint(b))
    def test_same_release_and_ambiguous_annual_excluded(self):
        self.assertIsNone(classify({'question':'Will US GDP growth in Q3 2026 be 2%?','description':'Advance Estimate'}))
        self.assertIsNone(classify({'question':'Negative GDP growth in 2026?','description':'annualized full-year GDP'}))
    def test_annual_gdp_rules_required(self):
        row={'question':'Will US GDP growth in 2026 be less than 0.5%?','description':'full-year real GDP growth rate from Q4 of 2026'}
        self.assertEqual(classify(row),'US_GDP_FULL_YEAR_2026')
        row['description']='Unrelated GDP'
        self.assertIsNone(classify(row))

if __name__=='__main__':unittest.main()
