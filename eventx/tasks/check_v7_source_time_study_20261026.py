from datetime import timedelta
import unittest
import numpy as np
from eventx.tasks.check_v7_live_quote_inputs_20261026 import T,row
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape,FEATURES,CONTRACT
from eventx.v7.source_time_study_20261026 import target_record,paired_summary,predict

class Tests(unittest.TestCase):
 def test_changed_and_unchanged(self):
  for bid,ask,expected in [(.4,.42,0),(.5,.52,1)]:
   tape=SourceTimeQuoteTape([row(T),row(T+timedelta(minutes=30),bid=bid,ask=ask)])
   self.assertEqual(target_record(tape,T.timestamp())['target'],expected)
 def test_unknown_stale_or_late(self):
  for r in [row(T+timedelta(minutes=27)),row(T+timedelta(minutes=30,seconds=1),source=T+timedelta(minutes=30))]:
   self.assertIsNone(target_record(SourceTimeQuoteTape([row(T),r]),T.timestamp())['target'])
 def test_endpoint_gate_does_not_remove_current(self):
  r=target_record(SourceTimeQuoteTape([row(T),row(T+timedelta(minutes=30))]),T.timestamp(),endpoint_gate=False)
  self.assertTrue(r['current_valid']);self.assertIsNone(r['target'])
 def test_future_endpoint_cannot_change_features(self):
  a=SourceTimeQuoteTape([row(T)]);b=SourceTimeQuoteTape([row(T),row(T+timedelta(minutes=30),bid=.5,ask=.52)])
  self.assertEqual(target_record(a,T.timestamp())['features'],target_record(b,T.timestamp())['features'])
 def test_missing_bounds_include_both_assignments(self):
  p={'global_rate':np.array([.2,.8]),'market_rate':np.array([.2,.8]),'full_logit':np.array([.2,.8]),'hgb7':np.array([.4,.6])}
  bounds=paired_summary([{'target':0},{'target':None}],p)['contrasts']['full_logit']['all_issued_gain_bounds']
  values=[paired_summary([{'target':0},{'target':y}],p)['contrasts']['full_logit']['log_loss_gain'] for y in [0,1]]
  np.testing.assert_allclose(bounds,[min(values),max(values)])
 def test_predict_never_accesses_target(self):
  class Est:
   def predict_proba(self,x):return np.tile([.75,.25],(len(x),1))
  bundle={'input_contract':CONTRACT,'features':FEATURES,'rate':.3,'market_rates':{},'full_logit':Est(),'hgb7':Est()}
  rr=[{'market_id':'new','features':[0.]*14}]
  self.assertEqual(predict(bundle,rr)['market_rate'][0],.3)
  bundle['input_contract']='old18'
  with self.assertRaises(ValueError):predict(bundle,rr)
if __name__=='__main__':unittest.main()
