from datetime import timedelta
import unittest
from eventx.tasks.check_v7_live_quote_inputs_20261026 import row,T
from eventx.v7.clock_bounded_quote_inputs_20261026 import SourceTimeQuoteTape,clock_health,CONTRACT
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape as Strict

class Tests(unittest.TestCase):
 def test_small_lead_is_not_permanently_discarded(self):
  r=row(T-timedelta(seconds=1),source=T-timedelta(seconds=.9))
  self.assertIsNone(Strict([r]).features(T.timestamp()));self.assertIsNotNone(SourceTimeQuoteTape([r]).features(T.timestamp()))
 def test_no_source_future_even_within_budget(self):
  self.assertIsNone(SourceTimeQuoteTape([row(T,source=T+timedelta(milliseconds=50))]).features(T.timestamp()))
 def test_no_unavailable_future(self):
  self.assertIsNone(SourceTimeQuoteTape([row(T+timedelta(milliseconds=50),source=T)]).features(T.timestamp()))
 def test_large_lead_fails_instead_of_falling_back(self):
  self.assertIsNone(SourceTimeQuoteTape([row(T-timedelta(seconds=5)),row(T-timedelta(seconds=1),source=T-timedelta(seconds=.7))]).features(T.timestamp()))
 def test_boundary(self):
  for lead,valid in [(250,True),(251,False)]:
   r=row(T-timedelta(seconds=1),source=T-timedelta(seconds=1)+timedelta(milliseconds=lead))
   self.assertEqual(SourceTimeQuoteTape([r]).features(T.timestamp()) is not None,valid)
 def test_freshness_unrelaxed(self):
  self.assertIsNone(SourceTimeQuoteTape([row(T-timedelta(seconds=121))]).features(T.timestamp()))
 def test_conflict_invalid_and_future_invariance(self):
  self.assertIsNone(SourceTimeQuoteTape([row(T),row(T,bid=.41)]).features(T.timestamp()))
  self.assertIsNone(SourceTimeQuoteTape([row(T,bid=0,ask=1)]).features(T.timestamp()))
  a=SourceTimeQuoteTape([row(T)]).features(T.timestamp());b=SourceTimeQuoteTape([row(T),row(T+timedelta(seconds=1))]).features(T.timestamp());self.assertEqual(a,b)
 def test_new_model_contract(self):
  self.assertEqual(SourceTimeQuoteTape([row(T)]).model_record(T.timestamp())['input_contract'],CONTRACT)
 def probe(self,t):
  return {'kind':'clock_probe','available_epoch':t,'measurements':[{'host':h,'exit_code':0,'offset_seconds':.06,'reported_uncertainty_seconds':u} for h,u in [('google',.01),('cloudflare',.08)]]}
 def test_clock_monitor_asof_stale(self):
  t=T.timestamp();p=self.probe(t)
  self.assertTrue(clock_health([p],t)[0]);self.assertFalse(clock_health([p],t-1)[0]);self.assertFalse(clock_health([p],t+361)[0])
 def test_clock_monitor_disagreement_and_large_offset(self):
  t=T.timestamp();p=self.probe(t);p['measurements'][1]['offset_seconds']=-.2
  self.assertFalse(clock_health([p],t)[0])
  for r in p['measurements']:r['offset_seconds']=.2
  self.assertFalse(clock_health([p],t)[0])
 def test_latest_failed_probe_invalidates(self):
  t=T.timestamp();p=self.probe(t);bad={'kind':'clock_probe','available_epoch':t+1,'measurements':[]}
  self.assertFalse(clock_health([p,bad],t+1)[0])
if __name__=='__main__':unittest.main()
