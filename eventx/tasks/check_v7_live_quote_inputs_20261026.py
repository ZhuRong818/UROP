"""Focused safety tests for the label-free quote input bridge."""
from datetime import datetime,timezone,timedelta
import unittest
from eventx.v7.live_quote_inputs_20261026 import FeatureTape,project_ws,InputCompatibilityError,transport_ready
T=datetime(2026,5,7,12,tzinfo=timezone.utc)
S=[{'market_id':'c','yes_asset_id':'Y','no_asset_id':'N'}]
def row(at,source=None,bid=.40,ask=.42):
 return {'market':b'c','asset_id':'Y','event_type':'price_change','timestamp_received':at,'timestamp':source or at,'best_bid':bid,'best_ask':ask}
def msg(kind='price_change',token='Y'):
 m={'event_type':kind,'market':'c','timestamp':str(int(T.timestamp()*1000)),'asset_id':token,'bids':[{'price':'.4','size':'10'}],'asks':[{'price':'.42','size':'10'}]}
 if kind=='price_change':m['price_changes']=[{'asset_id':token,'best_bid':'.40009','best_ask':'.42009'}]
 return m
class Tests(unittest.TestCase):
 def test_projection_and_guard(self):
  rr=project_ws(msg(),T.isoformat(),T.isoformat(),S);self.assertEqual(float(rr[0]['best_bid']),.4)
  tape=FeatureTape(rr);self.assertIsNotNone(tape.features(T.timestamp()))
  with self.assertRaises(InputCompatibilityError):tape.model_inputs(T.timestamp())
 def test_book_is_not_imputed(self):
  rr=project_ws(msg('book'),T.isoformat(),T.isoformat(),S);self.assertIsNone(rr[0]['best_bid']);self.assertIsNone(FeatureTape(rr).features(T.timestamp()))
 def test_no_asset_filtered_and_unknown_rejected(self):
  self.assertEqual(project_ws(msg(token='N'),T.isoformat(),T.isoformat(),S),[])
  with self.assertRaises(InputCompatibilityError):project_ws(msg(token='unknown'),T.isoformat(),T.isoformat(),S)
 def test_market_and_schema_fail_closed(self):
  m=msg();m['market']='wrong'
  with self.assertRaises(InputCompatibilityError):project_ws(m,T.isoformat(),T.isoformat(),S)
  with self.assertRaises(InputCompatibilityError):project_ws(msg('new_type'),T.isoformat(),T.isoformat(),S)
 def test_availability_rounding_never_backdates(self):
  at=T+timedelta(microseconds=100);rr=project_ws(msg(),at.isoformat(),T.isoformat(),S)
  self.assertGreaterEqual(rr[0]['timestamp_received'],at);self.assertIsNone(FeatureTape(rr).features(T.timestamp()))
  with self.assertRaises(InputCompatibilityError):project_ws(msg(),T.isoformat(),at.isoformat(),S)
 def test_source_and_receipt_ages(self):
  self.assertIsNone(FeatureTape([row(T,T-timedelta(seconds=121))]).features(T.timestamp()))
  self.assertIsNone(FeatureTape([row(T)]).features(T.timestamp()+121))
  self.assertIsNone(FeatureTape([row(T,T+timedelta(seconds=1))]).features(T.timestamp()))
 def test_ties_invalid_and_no_last_row_selection(self):
  self.assertIsNone(FeatureTape([row(T),row(T,bid=.41)]).features(T.timestamp()))
  f=FeatureTape([row(T),row(T)]).features(T.timestamp());self.assertAlmostEqual(f[7],__import__('math').log(2))
 def test_null_event_resets_quote(self):
  rr=[row(T),row(T+timedelta(seconds=1),bid=None,ask=None)];self.assertIsNone(FeatureTape(rr).features(T.timestamp()+1))
 def test_missing_lag_and_future_invariance(self):
  f=FeatureTape([row(T)]).features(T.timestamp());self.assertEqual([f[i] for i in [11,14,17]],[1.,1.,1.])
  self.assertEqual(f,FeatureTape([row(T),row(T+timedelta(seconds=1),bid=.60,ask=.62)]).features(T.timestamp()))
 def test_midnight_reset(self):
  t=T.replace(hour=0);rr=[row(t-timedelta(seconds=60)),row(t)];f=FeatureTape(rr).features(t.timestamp());self.assertEqual(f[7],__import__('math').log(2));self.assertEqual(f[17],1.)
 def test_transport_warmup_and_disconnection(self):
  t=T.timestamp();records=[{'kind':'ws_connected','at':(T-timedelta(seconds=1900)).isoformat()},{'kind':'ws_pong','at':(T-timedelta(seconds=5)).isoformat()}]
  self.assertTrue(transport_ready(records,t)[0]);records.append({'kind':'ws_disconnected','at':T.isoformat()});self.assertFalse(transport_ready(records,t)[0])
 def test_mixed_contract_rejected(self):
  with self.assertRaises(InputCompatibilityError):FeatureTape([row(T),*project_ws(msg(),T.isoformat(),T.isoformat(),S)])
if __name__=='__main__':unittest.main()
