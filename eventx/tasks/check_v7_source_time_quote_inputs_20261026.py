"""No labels: test common representation under different grouping and repeated events."""
from datetime import timedelta
import unittest
from eventx.tasks.check_v7_live_quote_inputs_20261026 import T,row,msg,S
from eventx.v7.live_quote_inputs_20261026 import project_ws
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape
class Tests(unittest.TestCase):
 def test_batch_and_duplicate_invariance_when_information_available(self):
  src=T-timedelta(seconds=10);a=row(src);b=row(T-timedelta(seconds=1),source=src)
  self.assertEqual(SourceTimeQuoteTape([a]).features(T.timestamp()),SourceTimeQuoteTape([b,b,b]).features(T.timestamp()))
 def test_delay_crossing_decision_remains_missing(self):
  delayed=row(T+timedelta(seconds=1),source=T-timedelta(seconds=1));self.assertIsNone(SourceTimeQuoteTape([delayed]).features(T.timestamp()))
 def test_conflicting_source_time_rejected(self):
  self.assertIsNone(SourceTimeQuoteTape([row(T),row(T,bid=.41)]).features(T.timestamp()))
 def test_old_out_of_order_update_does_not_replace_latest_source(self):
  latest=row(T-timedelta(seconds=2));old=row(T-timedelta(seconds=1),source=T-timedelta(seconds=100),bid=.5,ask=.52)
  self.assertEqual(SourceTimeQuoteTape([latest]).features(T.timestamp()),SourceTimeQuoteTape([latest,old]).features(T.timestamp()))
 def test_new_invalid_quote_does_not_fall_back(self):
  self.assertIsNone(SourceTimeQuoteTape([row(T-timedelta(seconds=1)),row(T,bid=0,ask=1)]).features(T.timestamp()))
 def test_book_event_does_not_define_new_quote_process(self):
  book=project_ws(msg('book'),T.isoformat(),T.isoformat(),S)
  self.assertEqual(SourceTimeQuoteTape([row(T)]).features(T.timestamp()),SourceTimeQuoteTape([row(T),*book]).features(T.timestamp()))
 def test_future_append_and_missing_lags(self):
  a=SourceTimeQuoteTape([row(T)]).features(T.timestamp());b=SourceTimeQuoteTape([row(T),row(T+timedelta(seconds=1),bid=.5,ask=.52)]).features(T.timestamp());self.assertEqual(a,b);self.assertEqual([a[i] for i in [7,10,13]],[1.,1.,1.])
 def test_freshness_and_clock(self):
  self.assertIsNone(SourceTimeQuoteTape([row(T-timedelta(seconds=121))]).features(T.timestamp()))
  self.assertIsNone(SourceTimeQuoteTape([row(T,source=T+timedelta(seconds=1))]).features(T.timestamp()))
 def test_explicit_new_contract(self):
  r=SourceTimeQuoteTape([row(T)]).model_record(T.timestamp());self.assertEqual(len(r['features']),14);self.assertFalse(r['compatible_with_frozen_18_feature_model']);self.assertTrue(r['requires_new_fit'])
if __name__=='__main__':unittest.main()
